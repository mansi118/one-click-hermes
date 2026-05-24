---
name: deploy-runbook
description: "Standard procedure for deploying or re-deploying NeuralEDGE Agent on a VPS — Ubuntu prereqs, one-line installer, Docker compose overlay, dashboard SSH tunnel, AWS Security Group settings, backup/restore. Load when the operator asks about installing, upgrading, moving, or recovering the agent."
version: 1.0.0
author: NeuralEDGE
license: MIT
metadata:
  hermes:
    tags: [neuraledge, deploy, ops, vps, aws, docker]
---

# Target environment

- **OS:** Ubuntu 22.04 LTS or 24.04 LTS, x86_64.
- **Sizing:** 2 vCPU / 4 GB RAM minimum; 8 GB recommended for browser-tool spikes.
- **Disk:** 20 GB. Most usage is the `~/.hermes` state + Docker images.
- **AWS:** EC2 `ap-south-1`, t3.medium (or graviton t4g.medium for cost).
- **Inbound rules (Security Group):** SSH/22 from operator IP **only**. Nothing else.

# One-line install

```
curl -fsSL https://get.neuraledge.in/agent | bash
```

This runs `neuraledge/install.sh`. The script is idempotent — re-running on an already
installed host is safe and resumes from the first incomplete step.

# Where things live

| Path | Contents |
|---|---|
| `/opt/neuraledge-agent` | Repo checkout |
| `~/.hermes/config.yaml` | Operator config (real Hermes schema: `model:`, `terminal:`, `skills.disabled:`, `display.skin:`, …) |
| `~/.hermes/.env` | Secrets (mode `600`) |
| `~/.hermes/SOUL.md` | Neural's persona (seeded from `neuraledge/branding/SOUL.md`) |
| `~/.hermes/mcp.json` | MCP server registration — cortex-mcp lives here |
| `~/.hermes/skins/neuraledge.yaml` | NeuralEDGE skin (banner, colors, branding strings) |
| `~/.hermes/skills/` | Learned skills (seed skills ship in repo `skills/neuraledge/`) |
| `~/.hermes/sessions/` | Tier-1 session memory + Honcho user model |
| `~/.hermes/cron/` | Operator-scheduled jobs |

# Compose overlay model

NeuralEDGE extends upstream's compose file rather than replacing it. The two compose
files together define the running stack:

```
docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml up -d
```

- **Upstream `docker-compose.yml`** — defines `gateway` and `dashboard` services on
  `network_mode: host` using the `hermes-agent` image.
- **Our `docker-compose.neuraledge.yml`** — adds the `cortex-mcp` service (also on
  host net, bound to `127.0.0.1:8765`).

# Dashboard access (SSH tunnel — never expose publicly)

The dashboard binds to `127.0.0.1:9119` on the VPS. Use an SSH local-forward:

```
ssh -L 9119:localhost:9119 ubuntu@<vps-host>
# then open http://localhost:9119
```

Do not edit compose to bind `0.0.0.0`. Do not add an inbound SG rule for 9119.

# Common commands

```
make up            # docker compose -f ... -f docker-compose.neuraledge.yml up -d
make down          # stop
make logs          # follow gateway logs
make doctor        # hermes doctor (the only green/red signal that counts)
make backup        # tar ~/.hermes
make sync-upstream # pull NousResearch, merge into our branch
```

# Switching CORTEX modes

In `~/.hermes/.env`:

```
CORTEX_MODE=stub              # canned data; works without NEOS endpoint
# or
CORTEX_MODE=live
CORTEX_ENDPOINT=https://...   # NEOS / Convex client API
CORTEX_TOKEN=...              # bearer
```

Then `docker compose ... restart cortex-mcp`. Verify with `cortex_status` from inside
the agent or `docker compose ... exec cortex-mcp python -m cortex_mcp.healthcheck`.

# Backup & restore

**Backup:** cron `0 3 * * * tar czf /var/backups/hermes-$(date +\%F).tar.gz -C ~ .hermes`
and ship the tarball off-host (S3 via the n8n backup workflow if configured).

**Restore on a new VPS:**
1. Run the installer (skips wizard if `~/.hermes` exists).
2. `tar xzf hermes-<date>.tar.gz -C ~`.
3. `make up`.
4. `make doctor`.

# Upgrading

```
make sync-upstream
# resolve conflicts only if NEURALEDGE_PATCHES.md lists any active core patches
make build
make up
make doctor
```

Pin upstream to a release tag (e.g. `v2026.5.16`) for reproducibility; chase
`upstream/main` only if you have a reason.

# Failure recovery

| Symptom | First check |
|---|---|
| Telegram silent | `make logs \| grep -i telegram`; re-pair if token rejected |
| Agent OOM | `free -h`; add swap or resize the instance |
| `cortex_*` tools hang | `cortex_status`; if all `down`, the breaker should already be open |
| Dashboard 502 | `docker compose ps`; ensure `gateway` is healthy, not just running |
| Disk full | `docker system prune`; rotate logs in `~/.hermes/logs/` |
| Lost `~/.hermes` | Restore from backup; do not redo the wizard — config will diverge |
