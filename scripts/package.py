#!/usr/bin/env python3
"""Package only source, documentation and example configuration."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def source_files(root=ROOT):
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if not p.is_file() or p.is_symlink() or any(v.startswith(".") or v == "__pycache__" for v in rel.parts[:-1]):
            continue
        if rel.parts[0] == "config":
            allowed = p.name.endswith((".example.json", ".example.yml"))
        elif rel.parts[0] == "terraform":
            allowed = p.name.endswith((".tf", ".tftest.hcl", ".example.tfvars")) or p.name == ".terraform.lock.hcl"
        elif rel.parts[0] in ("docs", "scripts", "tests"):
            allowed = p.suffix in (".md", ".py", ".sh")
        else:
            allowed = p.name in ("README.md", ".gitignore")
        if allowed:
            yield p, rel


def main():
    output = ROOT.parent / "oci-secure-workflows.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p, rel in source_files():
            z.write(p, Path("oci-secure-workflows") / rel)
    print(output)


if __name__ == "__main__":
    main()
