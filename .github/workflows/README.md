# CI/CD — `ci-cd.yml` (I2)

Push to `main` → build/test → push to GHCR → deploy needs manual
approval. PRs run the same tests but never reach build/deploy.

```
test-backend ─┐
               ├─→ build-and-push ─→ deploy (needs manual approval)
test-frontend ┘
```

## One-time repo setup (do this before the workflow can deploy)

**1. Create the `production` Environment** (this is what actually gates
`deploy` on manual approval — nothing in the YAML enforces it otherwise):
Settings → Environments → New environment → name it `production` → add
yourself as a required reviewer.

**2. Add two repo secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | the VPS's public IPv4 (`terraform output -raw server_ipv4`) |
| `DEPLOY_SSH_KEY` | private key of the dedicated deploy keypair (not your personal one) — its public half is attached automatically to every server `infra/terraform` creates via the `ci_deploy_public_key` variable, so it survives every `down.sh` + `up.sh` cycle without re-adding by hand |

`GITHUB_TOKEN` (used to push to GHCR) is automatic — nothing to add for that.

## Why a dedicated deploy key, and why GHCR auth needs nothing

Your personal SSH key never needs to leave your machine — CI gets its
own keypair, scoped to exactly this purpose, so revoking CI's access
later (compromised runner, retiring this workflow) never touches your
own access to the box. GHCR push auth reuses `GITHUB_TOKEN` (scoped
`packages: write` in the job) instead of a personal access token,
since it's already scoped to this repo and rotates automatically —
one less long-lived secret to manage.

## Why `helm upgrade --install --reuse-values --set image.tag=...`

The chart's other values (repository names, resource limits,
`knowledgeBase.hostPath`, etc.) don't change between deploys —
`--reuse-values` keeps whatever's already live and only the two image
tags get overridden, pinned to `github.sha` instead of floating
`:latest`. `infra/helm/README.md`'s original `helm install` (still
`:latest` + `imagePullPolicy: Always`) was flagged there as a
stand-in until CI existed; this replaces it.

## What still needs a human even after this merges

- Deploying still requires clicking "Approve" in the Environment's
  review UI (`production`) — by design, per SPEC.md's CI/CD decision.
- `infra/scripts/up.sh`/`down.sh` (billing on/off) are unrelated to
  this workflow and still run manually.
