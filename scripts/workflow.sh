#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
OCI_ACCESS_CONFIG=${OCI_ACCESS_CONFIG:-"$ROOT/config/access.json"}

if [ "$#" -eq 0 ]; then
  cat <<'USAGE'
Usage: sh scripts/workflow.sh COMMAND ...
  list | doctor | validate | plan TARGET | connect TARGET [--execute]
  ssh-config TARGET
  sshuttle TARGET --cidr 10.0.1.0/24 [--dns] [--execute]
  tailscale status|connect|accept-routes [--execute]
  tailscale advertise --cidr 10.0.1.0/24 [--execute]
  cloudflare validate|run --config FILE [--tunnel NAME] [--execute]
  cloudflare run --token-file FILE [--protocol auto|quic|http2] [--execute]
  worksheet --url https://SERVICE/ords/sql-developer [--local-port 18443] [--execute]
  infra STACK init|validate|plan|show|apply
Network commands preview by default. Set OCI_ACCESS_CONFIG for an alternate access JSON.
USAGE
  exit 0
fi
command_name=$1
shift
case "$command_name" in
  list|doctor|validate|plan|connect|ssh-config)
    exec "$PYTHON_BIN" "$ROOT/scripts/access.py" --config "$OCI_ACCESS_CONFIG" "$command_name" "$@"
    ;;
  sshuttle)
    exec "$PYTHON_BIN" "$ROOT/scripts/network.py" sshuttle --access-config "$OCI_ACCESS_CONFIG" "$@"
    ;;
  tailscale|cloudflare)
    exec "$PYTHON_BIN" "$ROOT/scripts/network.py" "$command_name" "$@"
    ;;
  infra)
    exec bash "$ROOT/scripts/infra.sh" "$@"
    ;;
  worksheet)
    exec "$PYTHON_BIN" "$ROOT/scripts/worksheet.py" "$@"
    ;;
  *) echo "Unknown command: $command_name" >&2; exit 2 ;;
esac
