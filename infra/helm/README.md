# Helm chart — k3s deployment (I1)

Deploys the backend (Flask + LangGraph RAG) and frontend (Vue3 + nginx)
onto the single-node k3s cluster provisioned by `infra/terraform` (I3).

## Prerequisites

1. **k3s installed on the VPS** — `curl -sfL https://get.k3s.io | sh -` run once via SSH.
2. **kubectl pointed at the cluster.** The k3s API (port 6443) is deliberately
   *not* opened in the Terraform firewall (I3) — only 22/80/443 are public.
   Reach it through an SSH tunnel instead:
   ```bash
   ssh -N -L 6443:localhost:6443 root@<server_ipv4> &
   ssh root@<server_ipv4> "cat /etc/rancher/k3s/k3s.yaml" | sed 's/127.0.0.1/localhost/' > ~/.kube/config-unsw-rag
   export KUBECONFIG=~/.kube/config-unsw-rag
   kubectl get nodes   # sanity check
   ```
3. **Knowledge base data on the node** (hostPath volume, single-node only):
   ```bash
   ssh root@<server_ipv4> "mkdir -p /opt/chatbot-data/knowledge_base"
   rsync -az data/knowledge_base/ root@<server_ipv4>:/opt/chatbot-data/knowledge_base/
   ```
4. **Images pushed to GHCR:**
   ```bash
   gh auth refresh -h github.com -s write:packages   # one-time, needs browser
   gh auth token | docker login ghcr.io -u <your-github-username> --password-stdin
   docker build -t ghcr.io/<owner>/unsw_rag_assistance-backend:latest -f backend/Dockerfile backend/
   docker build -t ghcr.io/<owner>/unsw_rag_assistance-frontend:latest -f frontend/Dockerfile frontend/
   docker push ghcr.io/<owner>/unsw_rag_assistance-backend:latest
   docker push ghcr.io/<owner>/unsw_rag_assistance-frontend:latest
   ```
   Then set both packages to **Public** visibility in GitHub → your profile →
   Packages → package settings, so the cluster can pull them without an
   `imagePullSecret`. (If you'd rather keep them private, create a
   `kubernetes.io/dockerconfigjson` secret and add `imagePullSecrets` to the
   deployment templates — not done here to keep the default path simple.)
5. **Secret with real credentials** — created imperatively, never templated
   into the chart (so nothing sensitive passes through `helm install --set`
   or a values file that could get committed):
   ```bash
   kubectl create namespace chatbot
   kubectl -n chatbot create secret generic chatbot-secrets \
     --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
     --from-literal=ADMIN_EMAIL="admin@unsw.edu.au" \
     --from-literal=ADMIN_PASSWORD="<pick-something-real>" \
     --from-literal=GOOGLE_API_KEY="<your-gemini-api-key>"
   ```

## Install

```bash
helm install chatbot infra/helm/chatbot -n chatbot \
  --set backend.image.repository=ghcr.io/<owner>/unsw_rag_assistance-backend \
  --set frontend.image.repository=ghcr.io/<owner>/unsw_rag_assistance-frontend
```

Check it came up:
```bash
kubectl -n chatbot get pods -w
kubectl -n chatbot logs -l app=backend --tail=50
```

Once both pods are `Running`/`Ready`, the app is reachable at
`http://<server_ipv4>/` — port 80 is already open in the Terraform
firewall and Traefik (k3s's bundled ingress controller) routes it to the
frontend Service, which proxies `/api` to the backend Service in-cluster.

## Upgrade after a new image push

Handled automatically by CI/CD (I2, `.github/workflows/ci-cd.yml`) now:
every push to `main` that passes tests builds and pushes `:<commit-sha>`,
and the `deploy` job (after manual approval) runs
`helm upgrade --install --reuse-values --set image.tag=<sha>` — real
immutable per-commit deploys, not the `:latest` + `imagePullPolicy: Always`
placeholder this section used to describe.

Manual equivalent, if you ever need to redeploy without pushing a new
commit (e.g. just to pick up a values.yaml change):
```bash
helm upgrade chatbot infra/helm/chatbot -n chatbot --reuse-values
```
