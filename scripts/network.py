#!/usr/bin/env python3
"""Preview or explicitly run optional private-network clients."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

from access import ROOT, load, private_routes, sshuttle_plan


def make_plan(args):
    notes = []
    prerequisite = None
    if args.method == "sshuttle":
        cfg = load(args.access_config)
        if args.target not in cfg["targets"]:
            raise ValueError("unknown SSH target")
        command = sshuttle_plan(cfg, args.target, private_routes(args.cidrs), args.dns)
        prerequisite = [sys.executable, str(ROOT / "scripts/access.py"), "--config",
                        str(Path(args.access_config).expanduser().resolve()), "connect", args.target, "--execute"]
        notes += ["First open the prerequisite Bastion tunnel in another terminal and verify SSH login.",
                  "sshuttle requires local firewall privileges and Python 3.10+ on the Linux VM.",
                  "Review local/corporate CIDR overlaps. Bastion TTL still applies."]
        if args.dns:
            notes.append("--dns can intercept DNS queries beyond the selected application; review corporate DNS behavior.")
    elif args.method == "tailscale":
        if args.action == "status":
            command = ["tailscale", "status"]
        elif args.action == "connect":
            command = ["tailscale", "up"]
            notes.append("Uses the installed Tailscale client; complete its interactive organization login.")
        elif args.action == "accept-routes":
            command = ["tailscale", "set", "--accept-routes"]
            notes.append("Accepts approved subnet routes on this client; review route overlap first (Linux clients).")
        else:
            command = ["tailscale", "set", "--advertise-routes=" + ",".join(private_routes(args.cidrs or []))]
            notes += ["Run on the intended OCI subnet-router VM, not on the developer laptop.",
                      "This replaces the advertised route list. Record existing routes before execution.",
                      "IP forwarding, route approval, access policy and client route acceptance are separate prerequisites."]
        if args.action != "advertise" and args.cidrs:
            raise ValueError("--cidr is only supported with tailscale advertise")
    else:
        config = str(Path(args.config).expanduser().resolve())
        command = ["cloudflared", "tunnel", "--config", config]
        if args.action == "validate":
            command += ["ingress", "validate"]
        else:
            if not args.tunnel or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.tunnel):
                raise ValueError("cloudflare run requires a tunnel name or UUID using letters, digits, _ or -")
            command += ["run", args.tunnel]
        notes += ["Uses a locally managed named tunnel and local credentials file; no token argument is accepted.",
                  "Create Access policy and DNS mapping separately before exposing an application."]
    return {"command": command, "prerequisite_command": prerequisite, "notes": notes}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="method", required=True)
    ssh = sub.add_parser("sshuttle")
    ssh.add_argument("target")
    ssh.add_argument("--access-config", default=str(ROOT / "config/access.json"))
    ssh.add_argument("--cidr", dest="cidrs", action="append", required=True)
    ssh.add_argument("--dns", action="store_true")
    ts = sub.add_parser("tailscale")
    ts.add_argument("action", choices=("status", "connect", "advertise", "accept-routes"))
    ts.add_argument("--cidr", dest="cidrs", action="append")
    cf = sub.add_parser("cloudflare")
    cf.add_argument("action", choices=("validate", "run"))
    cf.add_argument("--config", required=True)
    cf.add_argument("--tunnel")
    for child in (ssh, ts, cf):
        child.add_argument("--execute", action="store_true")
        child.add_argument("--json", action="store_true", help="preview only, machine-readable command")
    return p


def main(argv=None, runner=subprocess.call):
    p = parser()
    args = p.parse_args(argv)
    if args.json and args.execute:
        p.error("--json is a preview format; do not combine with --execute")
    plan = make_plan(args)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False))
        return 0
    if plan["prerequisite_command"]:
        print("Prerequisite (separate terminal): " + shlex.join(plan["prerequisite_command"]))
    for note in plan["notes"]:
        print(note)
    print(shlex.join(plan["command"]), flush=True)
    if not args.execute:
        print("Preview only. Add --execute to run this command; no changes were made.")
        return 0
    if not shutil.which(plan["command"][0]):
        raise ValueError(f'missing executable: {plan["command"][0]}; install it separately')
    if args.method == "cloudflare" and not Path(args.config).expanduser().is_file():
        raise ValueError("Cloudflare config file does not exist")
    return runner(plan["command"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
