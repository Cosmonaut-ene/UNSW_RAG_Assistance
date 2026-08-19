# Terraform — VPS provisioning (I3)

Scope is deliberately narrow (SPEC.md §2): provision one Hetzner Cloud VPS,
a firewall (22/80/443 only), and upload an SSH key. It does **not** install
k3s or deploy the app (that's I1/I2). DNS is also out of scope for now —
no domain has been decided yet (SPEC.md §0 says "start on the bare IP").
When a domain exists, the plan is to add a DNS provider block here and
point an A record at `server_ipv4` below.

## Prerequisites

1. A Hetzner Cloud API token (Read & Write) — Console → Security → API Tokens.
   **Never paste this into chat or commit it.** Export it as an env var:
   ```bash
   export TF_VAR_hcloud_token="your-token-here"
   ```
2. An SSH key pair (`~/.ssh/id_ed25519` / `.pub` — already present on this machine).
3. Terraform itself. Not installed locally on this machine — easiest is
   the official Docker image, no local install needed:
   ```bash
   alias tf='docker run --rm -it \
     -v "$(pwd):/workspace" -w /workspace \
     -v "$HOME/.ssh:/root/.ssh:ro" \
     -e TF_VAR_hcloud_token \
     hashicorp/terraform:1.9'
   ```
   Run this `alias` line (or put it in your shell rc), then use `tf` in
   place of `terraform` for every command below, from inside
   `infra/terraform/`.

## Commands

```bash
cd infra/terraform
tf init
tf plan      # review before applying -- share this output for review if you want a second look
tf apply     # you type "yes" to confirm; this is the step that actually spends money
```

`tf apply` prints `server_ipv4` in its output — that's the box I1 (k3s
install) targets next.

## Teardown

```bash
tf destroy
```
Deletes the VPS. Do this if you want to stop paying for it — Hetzner
bills hourly, so there's no cost to destroying between work sessions and
re-applying later (you'll get a new IP each time, though).
