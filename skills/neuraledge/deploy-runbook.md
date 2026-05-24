---
name: deploy-runbook
description: Standard procedure for deploying or re-deploying NeuralEDGE Agent on a VPS — Ubuntu prereqs, one-line installer, Docker compose, dashboard SSH tunnel, AWS Security Group settings, backup/restore. Load when the operator asks about installing, upgrading, moving, or recovering the agent.
pinned: true
priority: 80
tags: [neuraledge, deploy, ops, vps, aws, docker]
version: 1.0.0
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

Steps the installer executes:

1. Pre-flight (OS, sudo, RAM check).
2. Install Docker Engine + Compose if absent; add operator to `docker` group.
3. Add 2 GB swap if RAM < 6 GB.
4. Clone/pull the `neuraledge` branch into `/opt/neuraledge-agent`.
5. Seed `~/.hermes/` from `neuraledge/config/` (only if absent).
6. Build the two Docker images.
7. Run the setup wizard (provider key, Telegram bot pairing).
8. Prompt for CORTEX/n8n secrets (or leave `CORTEX_MODE=stub`).
9. `docker compose up -d` both services.
10. `docker compose exec hermes hermes doctor` and print the success banner.

# Where things live

| Path | Contents |
|---|---|
| `/opt/neuraledge-agent` | Repo checkout |
| `~/.hermes/config.yaml` | Operator config |
| `~/.hermes/.env` | Secrets (mode `600`) |
| `~/.hermes/sessions/` | Tier-1 session memory + Honcho user model |
| `~/.hermes/skills/` | Learned skills (seed skills live in repo `skills/neuraledge/`) |
| `docker volume hermes-data` | Mirrors `~/.hermes` into the container |

# Dashboard access (SSH tunnel — never expose publicly)

```
ssh -L 9119:localhost:9119 ubuntu@<vps-host>
# then open http://localhost:9119
```

The dashboard binds to `127.0.0.1` on the VPS. Do not edit compose to bind `0.0.0.0`,
do not add an inbound SG rule, do not run with `--insecure`. The tunnel is the path.

# Common commands

```
make up          # start both services
make down        # stop
make logs        # follow hermes logs (secrets redacted)
make doctor      # hermes self-check
make backup      # tar ~/.hermes
make sync-upstream  # pull NousResearch, merge into neuraledge branch
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

Then `docker compose restart cortex-mcp`. Verify with `cortex_status` from inside the
agent or `docker compose exec cortex-mcp python -m cortex_mcp.healthcheck`.

# Backup & restore

**Backup:** cron `0 3 * * * tar czf /var/backups/hermes-$(date +\%F).tar.gz -C ~ .hermes`
and ship the tarball to S3 (use the n8n backup workflow if configured).

**Restore on a new VPS:**
1. Run the installer (skips wizard if `~/.hermes` exists).
2. `tar xzf hermes-<date>.tar.gz -C ~`.
3. `docker compose up -d`.
4. `make doctor`.

# Upgrading

```
make sync-upstream
# resolve conflicts only if NEURALEDGE_PATCHES.md lists any active core patches
docker compose build
docker compose up -d
make doctor
```

See `docs/UPGRADING.md` for the full release checklist.

# Failure recovery

| Symptom | First check |
|---|---|
| Telegram silent | `docker compose logs hermes \| grep -i telegram`; re-pair if token rejected |
| Agent OOM | `free -h`; add swap or resize the instance |
| `cortex_*` tools hang | `cortex_status`; if all `down`, breaker should already be open |
| Dashboard 502 | `docker compose ps`; ensure `hermes` is healthy, not just running |
| Disk full | `docker system prune`; rotate logs in `~/.hermes/logs/` |
| Lost `~/.hermes` | Restore from backup; do not redo the wizard — config will diverge |
