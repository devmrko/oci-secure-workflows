import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("worksheet", ROOT / "scripts/worksheet.py")
worksheet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worksheet)


class WorksheetTests(unittest.TestCase):
    def test_mapping_preserves_original_https_origin_and_tls_checks(self):
        url = "https://example.adb.ap-seoul-1.oraclecloudapps.com/ords/sql-developer"
        cmd = worksheet.browser_command(url, 18443, "/browser path/chrome", "/tmp/profile path")
        self.assertEqual(cmd[-1], url)
        self.assertIn("--host-resolver-rules=MAP example.adb.ap-seoul-1.oraclecloudapps.com:443 127.0.0.1:18443", cmd)
        self.assertIn("--user-data-dir=/tmp/profile path", cmd)
        self.assertFalse(any("ignore-certificate" in x or "disable-web-security" in x for x in cmd))

    def test_rejects_credentials_ip_non_https_and_rule_injection(self):
        for url in ["http://service.example/", "https://127.0.0.1/",
                    "https://user:secret@service.example/", "https://service.example:8443/",
                    "https://service.example/?token=secret", "https://service.example/#token",
                    "https://bad,MAP other.example/", "https://bad%20name.example/"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                worksheet.browser_command(url, 18443, "chrome", "/tmp/profile")
        for port in [0, 443, 65536]:
            with self.assertRaises(ValueError):
                worksheet.browser_command("https://service.example/", port, "chrome", "/tmp/profile")

    def test_preview_never_launches_or_creates_profile(self):
        with patch.object(worksheet.subprocess, "call") as run, \
                patch.object(worksheet.tempfile, "TemporaryDirectory") as temp, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(worksheet.main(["--url", "https://service.example/ords/sql-developer"]), 0)
            run.assert_not_called()
            temp.assert_not_called()


if __name__ == "__main__":
    unittest.main()
