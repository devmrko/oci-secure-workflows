import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CF = os.environ.get("CLOUDFLARED_BIN")


@unittest.skipUnless(CF, "set CLOUDFLARED_BIN to validate the real Cloudflare config parser")
class CloudflareContractTests(unittest.TestCase):
    def run_ingress(self, *args):
        return subprocess.run([CF, "tunnel", "--config", str(ROOT / "config/cloudflared.example.yml"),
                               "ingress", *args], capture_output=True, text=True, check=True)

    def test_real_config_validation(self):
        result = self.run_ingress("validate")
        self.assertIn("OK", result.stdout + result.stderr)

    def test_expected_host_routes_to_private_service(self):
        result = self.run_ingress("rule", "https://app.example.com/health")
        self.assertIn("http://10.0.1.10:8080", result.stdout + result.stderr)

    def test_unknown_host_is_caught_by_404_rule(self):
        result = self.run_ingress("rule", "https://unknown.example.com/health")
        self.assertIn("http_status:404", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
