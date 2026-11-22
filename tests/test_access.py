import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("access", ROOT / "scripts/access.py")
access = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(access)
SID = "ocid1.bastionsession.oc1.ap-seoul-1.session"
DEST = SID + "@host.bastion.ap-seoul-1.oci.oraclecloud.com"
ACTIVE = {"id": SID, "lifecycle-state": "ACTIVE",
          "ssh-metadata": {"command": "ssh -i <privateKey> -N -L <localPort>:10.0.1.10:22 " + DEST}}


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.raw = json.loads((ROOT / "config/access.example.json").read_text())
        private = self.dir / "key with space"
        private.write_text("not-a-real-key")
        private.chmod(0o600)
        public = self.dir / "key with space.pub"
        public.write_text("ssh-ed25519 AAAA fake\n")
        self.raw["regions"]["ap-seoul-1"].update(private_key=str(private), public_key=str(public))
        self.config = self.dir / "access.json"
        self.config.write_text(json.dumps(self.raw))
        self.cfg = access.load(self.config)

    def quiet(self):
        return contextlib.redirect_stdout(io.StringIO())

    def test_default_preview_never_calls_oci_or_ssh(self):
        with patch.object(access.subprocess, "run", side_effect=AssertionError("process invoked")), \
             patch.object(access.subprocess, "call", side_effect=AssertionError("SSH invoked")), self.quiet():
            for args in (["list"], ["validate"], ["plan", "dev-ssh"],
                         ["connect", "seoul-socks"], ["ssh-config", "dev-ssh"]):
                self.assertEqual(access.main(["--config", str(self.config)] + args), 0)

    def test_invalid_public_loopback_linklocal_targets_rejected(self):
        for host in ("8.8.8.8", "127.0.0.1", "169.254.169.254", "::1", "10.0.1.10;id"):
            with self.subTest(host=host):
                self.raw["targets"]["dev-ssh"]["host"] = host
                self.config.write_text(json.dumps(self.raw))
                with self.assertRaises(ValueError):
                    access.load(self.config)

    def test_invalid_port_ttl_mode_and_config_injection(self):
        mutations = [("local_port", 0), ("local_port", True), ("mode", "unknown"),
                     ("user", "opc\nProxyCommand evil")]
        for key, value in mutations:
            cfg = copy.deepcopy(self.raw)
            cfg["targets"]["dev-ssh"][key] = value
            self.config.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError):
                access.load(self.config)
        self.raw["regions"]["ap-seoul-1"]["ttl_seconds"] = 10801
        self.config.write_text(json.dumps(self.raw))
        with self.assertRaises(ValueError):
            access.load(self.config)

    def test_cli_modes_use_correct_flags_and_separate_arguments(self):
        forward = access.create_command(self.cfg, "dev-ssh")
        self.assertIn("--session-ttl", forward)
        self.assertNotIn("--session-ttl-in-seconds", forward)
        self.assertEqual(forward[forward.index("--target-port") + 1], "22")
        socks = access.create_command(self.cfg, "seoul-socks")
        self.assertIn("--session-ttl-in-seconds", socks)
        detail = json.loads(socks[socks.index("--key-details") + 1])
        self.assertEqual(detail["publicKeyContent"], "ssh-ed25519 AAAA fake")
        self.assertEqual(forward[forward.index("--max-retries") + 1], "0")

    def test_loopback_only_and_host_verification_not_disabled(self):
        for name in ("dev-ssh", "seoul-socks"):
            cmd = access.ssh_command(self.cfg, name, DEST)
            self.assertTrue(any(s.startswith("127.0.0.1:") for s in cmd))
            self.assertIn("ExitOnForwardFailure=yes", cmd)
            self.assertFalse(any("StrictHostKeyChecking=no" in s or "UserKnownHostsFile=/dev/null" in s for s in cmd))
            self.assertEqual(cmd[-1], DEST)

    def test_server_metadata_command_is_never_executed(self):
        item = copy.deepcopy(ACTIVE)
        item["ssh-metadata"]["command"] += " ; touch /tmp/should-not-exist"
        self.assertEqual(access.destination_from_metadata(item), DEST)
        item["ssh-metadata"]["command"] = "ssh attacker@evil.example"
        with self.assertRaises(ValueError):
            access.destination_from_metadata(item)

    def test_session_state_progression_and_failure(self):
        runner = Mock(side_effect=[{"lifecycle-state": "CREATING"}, ACTIVE])
        sleep = Mock()
        self.assertEqual(access.wait_active([], SID, runner=runner, sleep=sleep), ACTIVE)
        sleep.assert_called_once_with(3)
        for state in ("FAILED", "DELETING", "DELETED"):
            with self.assertRaises(RuntimeError):
                access.wait_active([], SID, runner=Mock(return_value={"lifecycle-state": state}))

    def test_activation_timeout_does_not_recreate_session(self):
        runner = Mock(return_value={"lifecycle-state": "CREATING"})
        clock = Mock(side_effect=[0, 0, 181])
        with self.assertRaises(TimeoutError):
            access.wait_active([], SID, runner=runner, sleep=Mock(), clock=clock)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("get", runner.call_args.args[0])

    def test_connect_creates_one_session_and_runs_only_constructed_ssh(self):
        runner = Mock(side_effect=[{"lifecycle-state": "ACTIVE", "max-session-ttl-in-seconds": 10800},
                                   {"id": SID}, ACTIVE])
        ssh = Mock(return_value=0)
        with patch.object(access.shutil, "which", return_value="/fake/bin"), \
             patch.object(access.subprocess, "run"), patch.object(access.socket, "socket"), self.quiet():
            self.assertEqual(access.connect(self.cfg, "dev-ssh", runner=runner, ssh_runner=ssh), 0)
        self.assertEqual(sum("create-port-forwarding" in x.args[0] for x in runner.call_args_list), 1)
        self.assertEqual(ssh.call_args.args[0][-1], DEST)

    def test_connect_rejects_socks_without_feature_before_create(self):
        runner = Mock(return_value={"lifecycle-state": "ACTIVE", "max-session-ttl-in-seconds": 10800,
                                    "dns-proxy-status": "DISABLED"})
        with patch.object(access.shutil, "which", return_value="/fake/bin"), \
             patch.object(access.subprocess, "run"), patch.object(access.socket, "socket"):
            with self.assertRaises(ValueError):
                access.connect(self.cfg, "seoul-socks", runner=runner)
        self.assertEqual(runner.call_count, 1)

    def test_connect_uncertain_create_failure_has_no_retry(self):
        runner = Mock(side_effect=[{"lifecycle-state": "ACTIVE", "max-session-ttl-in-seconds": 10800},
                                   TimeoutError("request timed out")])
        with patch.object(access.shutil, "which", return_value="/fake/bin"), \
             patch.object(access.subprocess, "run"), patch.object(access.socket, "socket"), self.quiet():
            with self.assertRaises(TimeoutError):
                access.connect(self.cfg, "dev-ssh", runner=runner)
        self.assertEqual(runner.call_count, 2)

    def test_nsg_preview_no_calls_and_merge_uses_etag(self):
        nsg = "ocid1.networksecuritygroup.oc1.ap-seoul-1.new"
        vnic = "ocid1.vnic.oc1.ap-seoul-1.target"
        runner = Mock(side_effect=[{"data": {"nsg-ids": ["old"]}, "etag": "version-1"}, {}])
        with self.quiet():
            access.attach_nsg(self.cfg, "ap-seoul-1", vnic, nsg, False, runner=runner)
            runner.assert_not_called()
            access.attach_nsg(self.cfg, "ap-seoul-1", vnic, nsg, True, runner=runner)
        cmd = runner.call_args.args[0]
        self.assertEqual(json.loads(cmd[cmd.index("--nsg-ids") + 1]), ["old", nsg])
        self.assertEqual(cmd[cmd.index("--if-match") + 1], "version-1")

    def test_nsg_missing_etag_refuses_update_and_existing_is_noop(self):
        nsg = "ocid1.networksecuritygroup.oc1.ap-seoul-1.new"
        vnic = "ocid1.vnic.oc1.ap-seoul-1.target"
        runner = Mock(return_value={"data": {"nsg-ids": []}, "etag": None})
        with self.assertRaises(ValueError):
            access.attach_nsg(self.cfg, "ap-seoul-1", vnic, nsg, True, runner=runner)
        self.assertEqual(runner.call_count, 1)
        runner = Mock(return_value={"data": {"nsg-ids": [nsg]}, "etag": "v1"})
        with self.quiet():
            access.attach_nsg(self.cfg, "ap-seoul-1", vnic, nsg, True, runner=runner)
        self.assertEqual(runner.call_count, 1)


if __name__ == "__main__":
    unittest.main()
