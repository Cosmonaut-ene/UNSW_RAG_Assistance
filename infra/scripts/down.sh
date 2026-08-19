#!/usr/bin/env bash
# infra/scripts/down.sh
#
# Tears down the whole demo environment to stop Hetzner billing. A merely
# *stopped* Hetzner server is still billed at the full hourly rate (only
# the underlying disk/IP allocation changes, not the price) -- the only
# way to actually save money is to destroy the VPS outright, which is
# what this does. Container images stay in GHCR untouched, so nothing
# needs rebuilding on the way back up -- see up.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/../terraform"
TUNNEL_PID_FILE="/tmp/unsw-rag-k3s-tunnel.pid"

if [[ -f "$TUNNEL_PID_FILE" ]]; then
  pid="$(cat "$TUNNEL_PID_FILE")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "Stopping SSH tunnel (pid $pid)..."
    kill "$pid"
  fi
  rm -f "$TUNNEL_PID_FILE"
fi

echo "Destroying Terraform-managed infrastructure..."
cd "$TF_DIR"
terraform destroy

echo "Done. Billing stops the moment the server is actually deleted (Hetzner bills hourly)."
