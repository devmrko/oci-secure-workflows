import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("access_sshuttle", ROOT / "scripts/access.py")
access = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(access)


class SshuttlePlanTests(unittest.TestCase):
    def setUp(self):
        self.cfg = access.load(ROOT / "config/access.example.json")

    def test_plan_uses_linux_vm_login_over_loopback_not_bastion_session(self):
        cmd = access.sshuttle_plan(self.cfg, "dev-ssh", ["10.0.1.0/24"])
        self.assertEqual(cmd[cmd.index("--remote") + 1], "opc@127.0.0.1:2222")
        self.assertIn("127.0.0.0/8", cmd)
        self.assertNotIn("--dns", cmd)
        ssh = shlex.split(cmd[cmd.index("--ssh-cmd") + 1])
        self.assertIn("HostKeyAlias=oci-ap-seoul-1-10.0.1.10", ssh)
        self.assertNotIn(self.cfg["regions"]["ap-seoul-1"]["bastion_id"], shlex.join(cmd))

    def test_rejects_non_ssh_targets(self):
        for target in ("dev-web", "seoul-socks"):
            with self.assertRaises(ValueError):
                access.sshuttle_plan(self.cfg, target, ["10.0.1.0/24"])

    def test_rejects_public_default_ipv6_noncanonical_and_injected_routes(self):
        for cidr in ("0.0.0.0/0", "8.8.8.0/24", "169.254.0.0/16", "::/0",
                     "10.0.1.3/24", "--dns", "10.0.1.0/24;id"):
            with self.subTest(cidr=cidr), self.assertRaises(ValueError):
                access.sshuttle_plan(self.cfg, "dev-ssh", [cidr])
        with self.assertRaises(ValueError):
            access.sshuttle_plan(self.cfg, "dev-ssh", [])

    def test_private_boundaries_deduplication_and_explicit_dns(self):
        routes = ["10.0.1.10/32", "172.16.0.0/12", "192.168.0.0/16", "10.0.1.10/32"]
        cmd = access.sshuttle_plan(self.cfg, "dev-ssh", routes, dns=True)
        self.assertEqual(cmd.count("10.0.1.10/32"), 1)
        self.assertIn("--dns", cmd)
        for cidr in ("172.0.0.0/8", "192.0.0.0/8"):
            with self.assertRaises(ValueError):
                access.sshuttle_plan(self.cfg, "dev-ssh", [cidr])

    def test_key_path_is_preserved_through_nested_shell_quoting(self):
        key = "/tmp/key with spaces and ' quote $(touch NEVER)"
        self.cfg["targets"]["dev-ssh"]["identity_file"] = key
        command = access.sshuttle_plan(self.cfg, "dev-ssh", ["10.0.1.0/24"])
        reconstructed = shlex.split(shlex.join(command))
        ssh = shlex.split(reconstructed[reconstructed.index("--ssh-cmd") + 1])
        self.assertEqual(ssh[ssh.index("-i") + 1], key)

    def test_preview_never_runs_process_or_network(self):
        output = io.StringIO()
        with patch.object(access.subprocess, "run", side_effect=AssertionError("process")), \
             patch.object(access.subprocess, "call", side_effect=AssertionError("process")), \
             patch.object(access.socket, "socket", side_effect=AssertionError("network")), \
             contextlib.redirect_stdout(output):
            status = access.main(["--config", str(ROOT / "config/access.example.json"),
                                  "sshuttle-plan", "dev-ssh", "--cidr", "10.0.1.0/24", "--json"])
        self.assertEqual(status, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["validation"], "command-preview-only")

    def test_actual_cli_and_openssh_config_parse_without_connecting(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/access.py"), "--config",
                                 str(ROOT / "config/access.example.json"), "sshuttle-plan", "dev-ssh",
                                 "--cidr", "10.0.1.0/24", "--json"],
                                capture_output=True, text=True, check=True)
        command = json.loads(result.stdout)["sshuttle_command"]
        ssh = shlex.split(command[command.index("--ssh-cmd") + 1])
        # -G prints the resolved configuration; it does not connect or authenticate.
        parsed = subprocess.run(ssh + ["-G", "-p", "2222", "opc@127.0.0.1"],
                                capture_output=True, text=True, check=True)
        self.assertIn("hostname 127.0.0.1", parsed.stdout)
        self.assertIn("port 2222", parsed.stdout)
        self.assertIn("hostkeyalias oci-ap-seoul-1-10.0.1.10", parsed.stdout)


if __name__ == "__main__":
    unittest.main()
