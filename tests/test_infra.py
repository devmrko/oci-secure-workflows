import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InfraWrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "scripts").mkdir()
        self.stack = self.root / "terraform/bastion"
        self.stack.mkdir(parents=True)
        shutil.copyfile(ROOT / "scripts/infra.sh", self.root / "scripts/infra.sh")
        self.log = self.root / "calls.jsonl"
        fake = self.root / "fake-terraform"
        fake.write_text('#!/usr/bin/env python3\nimport json,os,sys\n'
                        'with open(os.environ["TEST_TF_LOG"],"a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n'
                        'sys.exit(int(os.environ.get("TEST_TF_EXIT","0")))\n')
        fake.chmod(0o700)
        self.env = dict(os.environ, TF_BIN=str(fake), TEST_TF_LOG=str(self.log))

    def run_wrapper(self, *args, input=""):
        return subprocess.run(["bash", str(self.root / "scripts/infra.sh"), *args],
                              input=input, text=True, capture_output=True, env=self.env)

    def test_unknown_stack_or_action_never_invokes_terraform(self):
        for args in (("../outside", "apply"), ("bastion", "destroy"), ("bastion",)):
            self.assertNotEqual(self.run_wrapper(*args).returncode, 0)
        self.assertFalse(self.log.exists())

    def test_apply_without_plan_or_wrong_confirmation_does_not_run(self):
        self.assertNotEqual(self.run_wrapper("bastion", "apply", input="bastion\n").returncode, 0)
        (self.stack / "review.tfplan").write_text("plan")
        self.assertNotEqual(self.run_wrapper("bastion", "apply", input="no\n").returncode, 0)
        self.assertFalse(self.log.exists())

    def test_apply_uses_saved_plan_and_consumes_it_on_success(self):
        (self.stack / "review.tfplan").write_text("reviewed-plan")
        result = self.run_wrapper("bastion", "apply", input="bastion\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.log.read_text())
        self.assertEqual(args[1:], ["apply", "-input=false", "review.tfplan"])
        self.assertFalse((self.stack / "review.tfplan").exists())
        self.assertTrue((self.stack / "review.tfplan.applied").exists())

    def test_failed_new_plan_cannot_leave_old_plan_applicable(self):
        (self.stack / "terraform.tfvars").write_text("example")
        (self.stack / "review.tfplan").write_text("old-plan")
        self.env["TEST_TF_EXIT"] = "1"
        self.assertNotEqual(self.run_wrapper("bastion", "plan").returncode, 0)
        self.assertFalse((self.stack / "review.tfplan").exists())
        self.assertEqual((self.stack / "review.tfplan.previous").read_text(), "old-plan")


class PackagingTests(unittest.TestCase):
    def test_only_examples_and_source_are_packaged(self):
        spec = importlib.util.spec_from_file_location("package", ROOT / "scripts/package.py")
        package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(package)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = ["config/access.json", "config/access.example.json", "config/cloudflared.yml",
                     "config/cloudflared.example.yml", "terraform/x/terraform.tfvars",
                     "terraform/x/terraform.example.tfvars", "terraform/x/review.tfplan.previous",
                     "terraform/x/.terraform/providers/private.tf", "terraform/x/.terraform.lock.hcl",
                     "terraform/x/terraform.tfstate", "scripts/access.py", "scripts/id.key"]
            for name in paths:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("placeholder")
            names = {str(rel) for _, rel in package.source_files(root)}
            self.assertEqual(names, {"config/access.example.json", "config/cloudflared.example.yml", "terraform/x/terraform.example.tfvars",
                                     "terraform/x/.terraform.lock.hcl", "scripts/access.py"})


if __name__ == "__main__":
    unittest.main()
