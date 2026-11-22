#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != "--clients" ]; }; then
  echo 'Usage: sh scripts/test.sh [--clients]' >&2
  exit 2
fi
if [ "${1:-}" = "--clients" ]; then
  "$PYTHON_BIN" -c 'import sshuttle'
  CLOUDFLARED_BIN=${CLOUDFLARED_BIN:-$(command -v cloudflared || true)}
  if [ -z "$CLOUDFLARED_BIN" ]; then
    echo 'cloudflared is required for --clients; set CLOUDFLARED_BIN or install the official CLI.' >&2
    exit 2
  fi
  export CLOUDFLARED_BIN
  "$CLOUDFLARED_BIN" --version
fi
cd "$ROOT"
sh -n scripts/workflow.sh
bash -n scripts/infra.sh
"$PYTHON_BIN" -m unittest discover -s tests -v
