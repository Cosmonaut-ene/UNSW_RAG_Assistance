# Infrastructure

- `terraform/` — provisions the Hetzner VPS (I3 in SPEC.md)
- `helm/chatbot/` — Helm chart deploying backend+frontend onto k3s (I1)
- `scripts/up.sh` / `scripts/down.sh` — the fast path for both, chained
  together, for spinning the whole demo up or down to control Hetzner
  billing between work sessions

## Cost control: down.sh / up.sh

A Hetzner Cloud server bills the same hourly rate whether it's running
or merely powered off -- stopping it doesn't save money, only deleting
it does. `down.sh` runs `terraform destroy`; `up.sh` reprovisions the
VPS, installs k3s, re-syncs the knowledge base data (never left the
VPS in git, so it has to go back up every time), and re-deploys via
Helm. Container images stay in GHCR the whole time, so nothing needs
rebuilding.

```bash
export TF_VAR_hcloud_token="..."   # once per shell session
./infra/scripts/down.sh            # when you're done for the day
./infra/scripts/up.sh               # next time you want the demo live again
```

Each `up.sh` run gets a **new IP address** (Hetzner doesn't guarantee
the same one back) -- fine for now on the bare IP, but worth knowing
before pointing a domain at it later.

See `terraform/README.md` and `helm/README.md` for what each step does
individually, and for the manual/first-time setup this script assumes
is already done once (SSH key on the machine, GHCR images pushed and
public, `.env` populated).
