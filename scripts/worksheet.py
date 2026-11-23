#!/usr/bin/env python3
"""Open an isolated Chrome/Chromium window through an existing HTTPS forward."""
import argparse
import ipaddress
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit


def browser_command(url, local_port, browser, profile):
    parts = urlsplit(url)
    host = parts.hostname or ""
    if (parts.scheme != "https" or parts.port not in (None, 443)
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment):
        raise ValueError("use an HTTPS URL on port 443 without credentials, query or fragment")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("use the original service FQDN, not an IP address")
    if (len(host) > 253 or "." not in host
            or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", p)
                       for p in host.split("."))):
        raise ValueError("invalid service FQDN")
    if not 1024 <= local_port <= 65535:
        raise ValueError("local port must be between 1024 and 65535")
    return [browser, "--user-data-dir=" + profile, "--no-first-run",
            "--no-default-browser-check", "--no-proxy-server", "--disable-quic",
            f"--host-resolver-rules=MAP {host}:443 127.0.0.1:{local_port}", url]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True)
    p.add_argument("--local-port", type=int, default=18443)
    default_browser = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                       if sys.platform == "darwin" else
                       shutil.which("google-chrome") or shutil.which("chromium") or "google-chrome")
    p.add_argument("--browser", default=default_browser)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    cmd = browser_command(args.url, args.local_port, args.browser, "<temporary-browser-profile>")
    print("Prerequisite: keep the HTTPS forward to the service private IP:443 running.")
    print(shlex.join(cmd), flush=True)
    if not args.execute:
        print("Preview only. Add --execute to open the isolated browser. No settings changed.")
        return 0
    if not shutil.which(args.browser):
        raise ValueError("Chrome/Chromium executable not found; specify --browser")
    with tempfile.TemporaryDirectory(prefix="oci-worksheet-browser-") as profile:
        cmd = browser_command(args.url, args.local_port, args.browser, profile)
        return subprocess.call(cmd)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
