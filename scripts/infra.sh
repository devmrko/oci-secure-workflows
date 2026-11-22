#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF_BIN="${TF_BIN:-terraform}"
usage() {
  echo 'Usage: bash scripts/infra.sh {bastion|load-balancer|api-gateway|nat} {init|validate|plan|show|apply}' >&2
}
[[ $# == 2 ]] || { usage; exit 2; }
case "$1" in bastion|load-balancer|api-gateway|nat) stack="$ROOT/terraform/$1" ;; *) usage; exit 2 ;; esac
case "$2" in
  init) exec "$TF_BIN" -chdir="$stack" init -input=false ;;
  validate) exec "$TF_BIN" -chdir="$stack" validate ;;
  plan)
    [[ -f "$stack/terraform.tfvars" ]] || { echo 'Copy terraform.example.tfvars to terraform.tfvars and edit it first.' >&2; exit 2; }
    # A failed/interrupted plan must never leave an older plan available for apply.
    if [[ -e "$stack/review.tfplan" ]]; then
      mv "$stack/review.tfplan" "$stack/review.tfplan.previous"
    fi
    exec "$TF_BIN" -chdir="$stack" plan -input=false -out=review.tfplan
    ;;
  show) exec "$TF_BIN" -chdir="$stack" show -no-color review.tfplan ;;
  apply)
    [[ -f "$stack/review.tfplan" ]] || { echo 'Create and review a saved plan first.' >&2; exit 2; }
    echo "This applies the saved OCI plan for $1. Type the stack name to continue:" >&2
    read -r answer
    [[ "$answer" == "$1" ]] || { echo 'Cancelled.' >&2; exit 2; }
    "$TF_BIN" -chdir="$stack" apply -input=false review.tfplan
    mv "$stack/review.tfplan" "$stack/review.tfplan.applied"
    ;;
  *) usage; exit 2 ;;
esac
