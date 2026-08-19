#!/usr/bin/env bash
# infra/scripts/up.sh
#
# Recreates the whole demo environment from scratch after down.sh tore it
# down: provision VPS (Terraform) -> install k3s -> tunnel kubectl access
# -> sync knowledge base data -> recreate secret -> helm install.
#
# Requires (same as the manual steps in infra/terraform/README.md and
# infra/helm/README.md, just chained together):
#   - TF_VAR_hcloud_token exported in this shell
#   - .env at the project root with SECRET_KEY/ADMIN_EMAIL/ADMIN_PASSWORD/GOOGLE_API_KEY
#   - terraform, kubectl, helm, ssh, rsync installed
#   - GHCR images already pushed and public (this script does not build/push
#     images -- they don't change just because the VPS was torn down)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TF_DIR="$SCRIPT_DIR/../terraform"
HELM_CHART="$SCRIPT_DIR/../helm/chatbot"
KUBECONFIG_FILE="$HOME/.kube/config-unsw-rag"
TUNNEL_PID_FILE="/tmp/unsw-rag-k3s-tunnel.pid"
REMOTE_DATA_DIR="/opt/chatbot-data/knowledge_base"

echo "==> 1/7 terraform apply"
cd "$TF_DIR"
terraform apply
SERVER_IP="$(terraform output -raw server_ipv4)"
echo "    server_ipv4 = $SERVER_IP"

# Purge any stale known_hosts entry for this IP before connecting. Hetzner
# can (and does) hand the same IP back to a *different*, brand-new server
# on a later `terraform apply` after down.sh destroyed the last one --
# same address, different host key. `StrictHostKeyChecking=accept-new`
# only auto-trusts hosts with NO existing entry; a *mismatched* existing
# entry (from the old server that used to live at this IP) still hard-fails
# with "REMOTE HOST IDENTIFICATION HAS CHANGED", and the wait loop below
# would spin on that error forever, looking exactly like a hang. Safe to
# purge unconditionally here because $SERVER_IP came straight out of
# `terraform output` above -- this is a box we just created, not an
# unknown host from user input.
ssh-keygen -f "$HOME/.ssh/known_hosts" -R "$SERVER_IP" >/dev/null 2>&1 || true

echo "==> 2/7 waiting for SSH..."
until ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes \
    "root@$SERVER_IP" true 2>/dev/null; do
  sleep 5
done

echo "==> 3/7 waiting for cloud-init, then installing k3s"
ssh "root@$SERVER_IP" "cloud-init status --wait >/dev/null; curl -sfL https://get.k3s.io | sh -"
ssh "root@$SERVER_IP" "until k3s kubectl get nodes >/dev/null 2>&1; do sleep 2; done"

echo "==> 4/7 opening SSH tunnel for kubectl (127.0.0.1:6443) -- port 6443 is deliberately NOT public"
ssh -N -L 6443:localhost:6443 "root@$SERVER_IP" &
echo $! > "$TUNNEL_PID_FILE"
sleep 2
ssh "root@$SERVER_IP" "cat /etc/rancher/k3s/k3s.yaml" | sed 's/127.0.0.1/localhost/' > "$KUBECONFIG_FILE"
chmod 600 "$KUBECONFIG_FILE"
export KUBECONFIG="$KUBECONFIG_FILE"
until kubectl get nodes >/dev/null 2>&1; do sleep 2; done

echo "==> 5/7 syncing knowledge base data (this VPS has none yet -- fresh box)"
ssh "root@$SERVER_IP" "mkdir -p $REMOTE_DATA_DIR"
rsync -az "$PROJECT_ROOT/data/knowledge_base/" "root@$SERVER_IP:$REMOTE_DATA_DIR/"

echo "==> 6/7 recreating namespace + secret from .env"
kubectl create namespace chatbot --dry-run=client -o yaml | kubectl apply -f -
set -a
# shellcheck disable=SC1091
source "$PROJECT_ROOT/.env"
set +a
kubectl -n chatbot create secret generic chatbot-secrets \
  --from-literal=SECRET_KEY="${SECRET_KEY}" \
  --from-literal=ADMIN_EMAIL="${ADMIN_EMAIL}" \
  --from-literal=ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  --from-literal=GOOGLE_API_KEY="${GOOGLE_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "==> 7/7 helm install (images already in GHCR from before down.sh -- nothing to rebuild)"
helm upgrade --install chatbot "$HELM_CHART" -n chatbot
kubectl -n chatbot wait --for=condition=Ready pod -l app=backend --timeout=300s
kubectl -n chatbot wait --for=condition=Ready pod -l app=frontend --timeout=120s

echo ""
echo "Up: http://$SERVER_IP/"
curl -s -o /dev/null -w "    health check: HTTP %{http_code}\n" "http://$SERVER_IP/api/admin/health"
