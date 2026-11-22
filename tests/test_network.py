import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import network


class NetworkTests(unittest.TestCase):
    def quiet(self):
        return contextlib.redirect_stdout(io.StringIO())

    def test_all_previews_do_not_execute(self):
        runner = Mock(side_effect=AssertionError("must not run"))
        for args in (["tailscale", "status"], ["tailscale", "connect"], ["tailscale", "accept-routes"],
                     ["tailscale", "advertise", "--cidr", "10.0.1.0/24"],
                     ["cloudflare", "run", "--config", "missing.yml", "--tunnel", "dev-app"],
                     ["cloudflare", "validate", "--config", "missing.yml"]):
            with self.quiet():
                self.assertEqual(network.main(args, runner=runner), 0)
        runner.assert_not_called()

    def test_execute_uses_only_argument_list_and_propagates_failure(self):
        runner = Mock(return_value=7)
        with patch.object(network.shutil, "which", return_value="/fake/tailscale"), self.quiet():
            self.assertEqual(network.main(["tailscale", "status", "--execute"], runner=runner), 7)
        runner.assert_called_once_with(["tailscale", "status"])

    def test_route_replacement_is_explicit_and_rejects_default_route(self):
        args = network.parser().parse_args(["tailscale", "advertise", "--cidr", "10.0.1.0/24"])
        plan = network.make_plan(args)
        self.assertEqual(plan["command"], ["tailscale", "set", "--advertise-routes=10.0.1.0/24"])
        self.assertTrue(any("replaces" in s for s in plan["notes"]))
        with self.assertRaises(ValueError), self.quiet():
            network.main(["tailscale", "advertise", "--cidr", "0.0.0.0/0"])
        with self.assertRaises(ValueError), self.quiet():
            network.main(["tailscale", "status", "--cidr", "10.0.1.0/24"])

    def test_cloudflare_missing_config_and_invalid_tunnel_block_execution(self):
        runner = Mock(side_effect=AssertionError("must not run"))
        with patch.object(network.shutil, "which", return_value="/fake/cloudflared"), self.quiet():
            with self.assertRaises(ValueError):
                network.main(["cloudflare", "validate", "--config", "/missing/config.yml", "--execute"], runner)
        for name in ("--token", "app;id", "$(id)", "app/name"):
            with self.assertRaises(ValueError), self.quiet():
                network.main(["cloudflare", "run", "--config", "file.yml", "--tunnel=" + name])
        runner.assert_not_called()

    def test_shell_entrypoint_previews_and_real_subprocess_wiring(self):
        with tempfile.TemporaryDirectory(prefix="workflow test ") as temp:
            directory = Path(temp)
            binary = directory / "bin"
            binary.mkdir()
            log = directory / "calls.jsonl"
            for name in ("sshuttle", "tailscale", "cloudflared"):
                executable = binary / name
                executable.write_text(f'#!{sys.executable}\nimport json,os,sys\n'
                                      'with open(os.environ["TEST_NETWORK_LOG"],"a") as f:\n'
                                      ' f.write(json.dumps(sys.argv)+"\\n")\n')
                executable.chmod(0o700)
            config = directory / "local tunnel.yml"
            config.write_text("ingress: []\n")
            env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                       PYTHON_BIN=sys.executable, OCI_ACCESS_CONFIG=str(ROOT / "config/access.example.json"),
                       TEST_NETWORK_LOG=str(log))
            commands = [
                ["sshuttle", "dev-ssh", "--cidr", "10.0.1.0/24"],
                ["tailscale", "status"],
                ["tailscale", "connect"],
                ["tailscale", "advertise", "--cidr", "10.0.1.0/24"],
                ["cloudflare", "validate", "--config", str(config)],
                ["cloudflare", "run", "--config", str(config), "--tunnel", "dev-app"],
                ["tailscale", "accept-routes"],
            ]
            for cmd in commands:
                subprocess.run(["sh", str(ROOT / "scripts/workflow.sh"), *cmd],
                               cwd=directory, env=env, check=True, capture_output=True, text=True)
            self.assertFalse(log.exists(), "preview unexpectedly ran a client")
            for cmd in commands:
                subprocess.run(["sh", str(ROOT / "scripts/workflow.sh"), *cmd, "--execute"],
                               cwd=directory, env=env, check=True, capture_output=True, text=True)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(calls), len(commands))
            self.assertIn("opc@127.0.0.1:2222", calls[0])
            self.assertEqual(calls[3][1:], ["set", "--advertise-routes=10.0.1.0/24"])
            self.assertEqual(calls[4][1:], ["tunnel", "--config", str(config.resolve()), "ingress", "validate"])
            self.assertEqual(calls[5][1:], ["tunnel", "--config", str(config.resolve()), "run", "dev-app"])
            self.assertEqual(calls[6][1:], ["set", "--accept-routes"])

    def test_shell_entrypoint_invokes_existing_access_cli(self):
        env = dict(os.environ, OCI_ACCESS_CONFIG=str(ROOT / "config/access.example.json"), PYTHON_BIN=sys.executable)
        for args in (["list"], ["connect", "dev-web"]):
            result = subprocess.run(["sh", str(ROOT / "scripts/workflow.sh"), *args],
                                    env=env, capture_output=True, text=True, check=True)
            self.assertIn("127.0.0.1", result.stdout)

    @unittest.skipUnless(importlib.util.find_spec("sshuttle"), "install sshuttle to validate its real option parser")
    def test_real_sshuttle_parser_accepts_generated_options(self):
        from sshuttle.options import parser
        args = network.parser().parse_args(["sshuttle", "dev-ssh", "--access-config",
                                            str(ROOT / "config/access.example.json"),
                                            "--cidr", "10.0.1.0/24", "--dns"])
        plan = network.make_plan(args)
        opts = parser.parse_args(plan["command"][1:])
        self.assertEqual(opts.remote, "opc@127.0.0.1:2222")
        self.assertTrue(opts.dns)
        self.assertEqual(opts.subnets[0][0][1:3], ("10.0.1.0", 24))


if __name__ == "__main__":
    unittest.main()
