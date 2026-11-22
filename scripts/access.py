#!/usr/bin/env python3
"""OCI Bastion access helper. Default commands are offline previews."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def identifier(value, pattern, label):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError(f"{label}: invalid value")
    return value


def port(value):
    if type(value) is not int or not 1 <= value <= 65535:
        raise ValueError("port must be an integer between 1 and 65535")
    return value


def key_path(value):
    if not isinstance(value, str) or not value or any(c in value for c in '\r\n\"'):
        raise ValueError("key path must be a nonempty path without quotes/newlines")
    return str(Path(value).expanduser().resolve())


def load(path):
    cfg = json.loads(Path(path).read_text())
    identifier(cfg["profile"], r"[A-Za-z0-9_.-]+", "profile")
    if not cfg.get("regions") or not cfg.get("targets"):
        raise ValueError("regions and targets must not be empty")
    for region, r in cfg["regions"].items():
        identifier(region, r"[a-z][a-z0-9-]+", "region")
        identifier(r["bastion_id"], r"ocid1\.bastion\.[A-Za-z0-9_.-]+", "bastion_id")
        for k in ("public_key", "private_key"):
            r[k] = key_path(r[k])
        ttl = r.get("ttl_seconds", 10800)
        if type(ttl) is not int or not 1800 <= ttl <= 10800:
            raise ValueError("ttl_seconds must be 1800..10800")
        r["ttl_seconds"] = ttl
    for name, t in cfg["targets"].items():
        identifier(name, r"[A-Za-z0-9][A-Za-z0-9_-]*", "target name")
        if t["region"] not in cfg["regions"]:
            raise ValueError(f"{name}: unknown region")
        port(t["local_port"])
        if t["mode"] == "forward":
            # Restrict this starter to RFC1918 IPv4; avoid public/metadata endpoints.
            host = ipaddress.ip_address(t["host"])
            private_networks = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
            if not any(host in ipaddress.ip_network(n) for n in private_networks):
                raise ValueError(f"{name}: host must be an RFC1918 IPv4 address")
            port(t["port"])
        elif t["mode"] != "socks":
            raise ValueError(f"{name}: mode must be forward or socks")
        if "user" in t:
            identifier(t["user"], r"[A-Za-z_][A-Za-z0-9_.-]*", "user")
        if "identity_file" in t:
            t["identity_file"] = key_path(t["identity_file"])
    return cfg


def oci_base(cfg, region):
    return ["oci", "--profile", cfg["profile"], "--region", region,
            "--output", "json", "--max-retries", "0", "--connection-timeout", "10", "--read-timeout", "30"]


def create_command(cfg, name):
    t = cfg["targets"][name]
    r = cfg["regions"][t["region"]]
    cmd = oci_base(cfg, t["region"]) + ["bastion", "session"]
    if t["mode"] == "forward":
        cmd += ["create-port-forwarding", "--target-private-ip", t["host"],
                "--target-port", str(t["port"]), "--ssh-public-key-file", r["public_key"],
                "--session-ttl", str(r["ttl_seconds"])]
    else:
        cmd += ["create-session-create-dynamic-port-forwarding-session-target-resource-details",
                "--key-type", "PUB", "--key-details",
                json.dumps({"publicKeyContent": Path(r["public_key"]).read_text().strip()}),
                "--session-ttl-in-seconds", str(r["ttl_seconds"])]
    return cmd + ["--bastion-id", r["bastion_id"], "--display-name", "oci-secure-workflows"]


def ssh_command(cfg, name, destination):
    t = cfg["targets"][name]
    r = cfg["regions"][t["region"]]
    cmd = ["ssh", "-i", r["private_key"], "-N", "-o", "IdentitiesOnly=yes",
           "-o", "ExitOnForwardFailure=yes", "-o", "ConnectTimeout=15",
           "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3"]
    if t["mode"] == "forward":
        cmd += ["-L", f'127.0.0.1:{t["local_port"]}:{t["host"]}:{t["port"]}']
    else:
        cmd += ["-D", f'127.0.0.1:{t["local_port"]}']
    return cmd + ["-p", "22", destination]


def run_json(command):
    p = subprocess.run(command, text=True, capture_output=True, timeout=50, check=False)
    if p.returncode:
        # CLI stderr may contain request metadata; keep it on the user's terminal only.
        raise RuntimeError(p.stderr.strip() or "OCI CLI command failed")
    return json.loads(p.stdout)["data"]


def run_full_json(command):
    p = subprocess.run(command, text=True, capture_output=True, timeout=50, check=False)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or "OCI CLI command failed")
    return json.loads(p.stdout)


def destination_from_metadata(session):
    sid = identifier(session["id"], r"ocid1\.bastionsession\.[A-Za-z0-9_.-]+", "session id")
    tokens = shlex.split(session["ssh-metadata"]["command"])
    matches = [v for v in tokens if re.fullmatch(re.escape(sid) + r"@[A-Za-z0-9][A-Za-z0-9.-]+", v)]
    if len(matches) != 1:
        raise ValueError("OCI SSH metadata has no unique session destination")
    # Only the destination is consumed. Never execute server-returned command text.
    return matches[0]


def wait_active(base, sid, timeout=180, runner=run_json, sleep=time.sleep, clock=time.monotonic):
    deadline = clock() + timeout
    while clock() < deadline:
        session = runner(base + ["bastion", "session", "get", "--session-id", sid])
        state = session["lifecycle-state"]
        if state == "ACTIVE":
            return session
        if state != "CREATING":
            raise RuntimeError(f"session is {state}; do not retry creation blindly")
        sleep(3)
    raise TimeoutError(f"session {sid} activation timed out; inspect it before retrying")


def show_plan(cfg, name):
    t = cfg["targets"][name]
    r = cfg["regions"][t["region"]]
    print(f'Profile={cfg["profile"]} Region={t["region"]} Bastion={r["bastion_id"]}')
    print(f'TTL={r["ttl_seconds"]}s; new session per execution; no automatic reconnect')
    print(f'Local endpoint: 127.0.0.1:{t["local_port"]} ({t["mode"]})')
    if t["mode"] == "forward":
        print(f'Target: {t["host"]}:{t["port"]}')
    print("SSH after session becomes ACTIVE:")
    print(shlex.join(ssh_command(cfg, name, "<session-id>@<host-from-OCI-ssh-metadata>")))
    print("Preview only. Use connect TARGET --execute to create a session and open SSH.")


def connect(cfg, name, runner=run_json, ssh_runner=subprocess.call):
    t = cfg["targets"][name]
    r = cfg["regions"][t["region"]]
    for binary in ("oci", "ssh", "ssh-keygen"):
        if not shutil.which(binary):
            raise ValueError(f"missing executable: {binary}")
    for k in ("private_key", "public_key"):
        if not Path(r[k]).is_file():
            raise ValueError(f'missing key file: {r[k]}')
    if os.name == "posix" and Path(r["private_key"]).stat().st_mode & 0o077:
        raise ValueError("private key permissions must exclude group/other (chmod 600)")
    # Check format using only the public key. Encrypted private keys remain supported.
    subprocess.run(["ssh-keygen", "-l", "-f", r["public_key"]],
                   stdout=subprocess.DEVNULL, check=True)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", t["local_port"]))
    base = oci_base(cfg, t["region"])
    bastion = runner(base + ["bastion", "bastion", "get", "--bastion-id", r["bastion_id"]])
    if bastion["lifecycle-state"] != "ACTIVE":
        raise ValueError("Bastion is not ACTIVE")
    if r["ttl_seconds"] > bastion["max-session-ttl-in-seconds"]:
        raise ValueError("requested TTL exceeds Bastion maximum")
    if t["mode"] == "socks" and bastion.get("dns-proxy-status") != "ENABLED":
        raise ValueError("enable FQDN/SOCKS5 support on this Bastion first")
    print("Creating one session. If this request times out, inspect OCI sessions before retrying.", flush=True)
    session = runner(create_command(cfg, name))
    sid = identifier(session["id"], r"ocid1\.bastionsession\.[A-Za-z0-9_.-]+", "session id")
    print(f"Session: {sid}", flush=True)
    cleanup = base + ["bastion", "session", "delete", "--session-id", sid]
    print("Cleanup after use: " + shlex.join(cleanup), flush=True)
    active = wait_active(base, sid, runner=runner)
    print("SSH stays in foreground. Ctrl+C ends the tunnel; session remains until deleted or TTL expires.", flush=True)
    return ssh_runner(ssh_command(cfg, name, destination_from_metadata(active)))


def ssh_config(cfg, name):
    t = cfg["targets"][name]
    if t["mode"] != "forward" or t["port"] != 22:
        raise ValueError("ssh-config requires a forward target on port 22")
    if "user" not in t or "identity_file" not in t:
        raise ValueError("SSH target requires user and identity_file")
    print(f'Host {name}\n    HostName 127.0.0.1\n    Port {t["local_port"]}\n'
          f'    User {t["user"]}\n    IdentityFile "{t["identity_file"]}"\n'
          f'    IdentitiesOnly yes\n    HostKeyAlias oci-{t["region"]}-{t["host"]}')


def private_routes(cidrs):
    private = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    routes = []
    for cidr in cidrs:
        network = ipaddress.ip_network(cidr, strict=True)
        if network.version != 4 or not any(network.subnet_of(n) for n in private):
            raise ValueError("sshuttle routes must be explicit RFC1918 IPv4 CIDRs")
        if str(network) not in routes:
            routes.append(str(network))
    if not routes:
        raise ValueError("at least one private CIDR is required")
    return routes


def sshuttle_plan(cfg, name, cidrs, dns=False):
    """Build an offline command; never start SSH or change local firewall rules."""
    t = cfg["targets"][name]
    if t["mode"] != "forward" or t.get("port") != 22:
        raise ValueError("sshuttle-plan requires a forward target on SSH port 22")
    if not t.get("user") or not t.get("identity_file"):
        raise ValueError("sshuttle-plan requires user and identity_file for the Linux VM")
    routes = private_routes(cidrs)
    ssh = ["ssh", "-F", "/dev/null", "-i", t["identity_file"],
           "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=15",
           "-o", f'HostKeyAlias=oci-{t["region"]}-{t["host"]}']
    cmd = ["sshuttle", "--remote", f'{t["user"]}@127.0.0.1:{t["local_port"]}',
           "--ssh-cmd", shlex.join(ssh), "--exclude", "127.0.0.0/8"]
    if dns:
        cmd.append("--dns")
    return cmd + routes


def attach_nsg(cfg, region, vnic_id, nsg_id, execute, runner=run_full_json):
    identifier(region, r"[a-z][a-z0-9-]+", "region")
    identifier(vnic_id, r"ocid1\.vnic\.[A-Za-z0-9_.-]+", "vnic id")
    identifier(nsg_id, r"ocid1\.networksecuritygroup\.[A-Za-z0-9_.-]+", "nsg id")
    base = oci_base(cfg, region)
    get = base + ["network", "vnic", "get", "--vnic-id", vnic_id]
    if not execute:
        print("Preview: read current VNIC, merge requested NSG into existing nsg-ids, update with --if-match ETag.")
        print(shlex.join(get))
        print(f"Add NSG: {nsg_id}. Existing memberships will be preserved. No calls made.")
        return
    # run_json strips headers. This mutation needs ETag, so retain the complete response.
    response = runner(get)
    vnic = response["data"]
    etag = response["etag"]
    if not etag:
        raise ValueError("missing ETag; refusing non-conditional VNIC update")
    existing = vnic.get("nsg-ids") or []
    if nsg_id in existing:
        print("NSG already attached; no update required")
        return
    if len(existing) >= 5:
        raise ValueError("VNIC already has five NSGs; review memberships manually")
    runner(base + ["network", "vnic", "update", "--vnic-id", vnic_id,
                  "--nsg-ids", json.dumps(existing + [nsg_id]), "--if-match", etag, "--force"])
    print("VNIC update accepted; verify membership and connectivity.")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=str(ROOT / "config/access.json"))
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    sub.add_parser("validate")
    sub.add_parser("doctor")
    for action in ("plan", "connect", "ssh-config"):
        q = sub.add_parser(action)
        q.add_argument("target")
        if action == "connect":
            q.add_argument("--execute", action="store_true")
    q = sub.add_parser("sshuttle-plan", help="print commands only; never starts sshuttle")
    q.add_argument("target")
    q.add_argument("--cidr", required=True, action="append", dest="cidrs")
    q.add_argument("--dns", action="store_true", help="include optional global DNS interception")
    q.add_argument("--json", action="store_true")
    n = sub.add_parser("attach-nsg")
    n.add_argument("--region", required=True)
    n.add_argument("--vnic-id", required=True)
    n.add_argument("--nsg-id", required=True)
    n.add_argument("--execute", action="store_true")
    a = p.parse_args(argv)
    cfg = load(a.config)
    if a.action == "validate":
        print("Configuration valid (offline; placeholder IDs and file existence not verified).")
    elif a.action == "doctor":
        missing = [b for b in ("oci", "ssh", "ssh-keygen") if not shutil.which(b)]
        for region, r in cfg["regions"].items():
            for k in ("public_key", "private_key"):
                print(f'{region} {k}: {"exists" if Path(r[k]).is_file() else "MISSING"}')
        print("Missing executables: " + (", ".join(missing) or "none"))
        print("Offline only. IAM, CIDR allowlist, routes and target firewall still need verification.")
    elif a.action == "list":
        for name, t in cfg["targets"].items():
            dest = f'{t["host"]}:{t["port"]}' if t["mode"] == "forward" else "SOCKS5"
            print(f'{name:20} {t["region"]:18} 127.0.0.1:{t["local_port"]} -> {dest}')
    elif a.action == "attach-nsg":
        attach_nsg(cfg, a.region, a.vnic_id, a.nsg_id, a.execute)
    else:
        if a.target not in cfg["targets"]:
            p.error(f"unknown target {a.target}; use list")
        if a.action == "ssh-config":
            ssh_config(cfg, a.target)
        elif a.action == "sshuttle-plan":
            command = sshuttle_plan(cfg, a.target, a.cidrs, a.dns)
            tunnel = [sys.executable, str(Path(__file__).resolve()), "--config",
                      str(Path(a.config).expanduser().resolve()), "connect", a.target, "--execute"]
            if a.json:
                print(json.dumps({"bastion_command": tunnel, "sshuttle_command": command,
                                  "validation": "command-preview-only"}, ensure_ascii=False))
            else:
                print("Terminal 1: open Bastion forwarding to the Linux VM:")
                print(shlex.join(tunnel))
                print("Terminal 2: after SSH login works, manually run:")
                print(shlex.join(command))
                print("Preview only. Linux VM needs Python 3.10+; local firewall privileges are required by sshuttle.")
                print("Bastion TTL still applies. Review CIDR overlaps and stop sshuttle before closing the tunnel.")
        elif a.action == "connect" and a.execute:
            return connect(cfg, a.target)
        else:
            show_plan(cfg, a.target)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped. Created OCI sessions remain until TTL or manual deletion.", file=sys.stderr)
        sys.exit(130)
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.SubprocessError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
