# NeuralEDGE Agent — Operations Runbook

The day-2 guide. The canonical version (loaded into Neural at runtime) lives at
`skills/neuraledge/deploy-runbook/SKILL.md`. This file is the human-readable expanded
form — keep them in sync when either changes.

---

## Layout on the VPS

| Path | Contents |
|---|---|
| `/opt/neuraledge-agent` | Git checkout of `main` (NeuralEDGE scaffold + merged upstream Hermes tag) |
| `~/.hermes/config.yaml` | Active Hermes config (seeded from `neuraledge/config/config.defaults.yaml`) |
| `~/.hermes/.env` | Secrets, mode `600` (seeded from `.env.template`) |
| `~/.hermes/SOUL.md` | Neural's persona (seeded from `neuraledge/branding/SOUL.md`) |
| `~/.hermes/config.yaml` *(`mcp_servers:` block)* | MCP server registry — cortex-mcp registered here |
| `~/.hermes/skins/neuraledge.yaml` | Active skin (seeded from `neuraledge/skins/`) |
| `~/.hermes/skills/neuraledge/<slug>/SKILL.md` | NeuralEDGE seed skills (4 of them) |
| `~/.hermes/skills/` | Plus skills learned at runtime |
| `~/.hermes/sessions/` | Tier-1 session memory + Honcho user model |
| `~/.hermes/workspace/` | Working files the agent creates |
| `~/.hermes/logs/` | Structured logs (secrets redacted) |
| `~/hermes-backups/` | `make backup` output |

Backing up `~/.hermes` is backing up the entire operator state.

---

## Daily ops

| Action | Command |
|---|---|
| Start | `make up` |
| Stop | `make down` |
| Restart | `make restart` |
| Follow gateway logs | `make logs` |
| Follow MCP bridge logs | `make logs-cortex` |
| Container status | `make ps` |
| Self-check | `make doctor`  (← the **only** green/red signal) |
| CORTEX health | `make cortex-status` |
| Backup | `make backup` |
| Drop into gateway shell | `make shell` |
| Tweak skill / skin / SOUL | edit files in repo, `make build`, `make restart` |

All `make` targets are thin wrappers around
`docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml …` — the compose
overlay model.

---

## Switching LLM provider

Edit `~/.hermes/config.yaml` `model:` block, and `~/.hermes/.env` for the API key:

```yaml
# ~/.hermes/config.yaml
model:
  default: "anthropic/claude-sonnet-4-6"
  provider: "anthropic"     # or "openrouter", "auto", "nous", etc.
```

Then `make restart`. For a one-off switch without editing files:

```bash
docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml \
  exec gateway hermes model anthropic/claude-sonnet-4-6
```

---

## Switching CORTEX-PALACE mode

**Stub → live:**

```bash
# Edit ~/.hermes/.env
CORTEX_MODE=live
CORTEX_ENDPOINT=https://cortex.neos.internal
CORTEX_TOKEN=<bearer>

docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml \
  restart cortex-mcp
make cortex-status   # expect mode=live, all tiers ok
```

**Live → stub** (e.g. for an outage drill or local dev):

```bash
# Edit ~/.hermes/.env: CORTEX_MODE=stub
make restart  # or just restart cortex-mcp
```

Neural detects the mode automatically — no agent restart needed for tool behaviour
change; new tool calls hit the updated client immediately.

---

## Dashboard access

Bound to `127.0.0.1:9119` on the VPS. Use an SSH local-forward — never expose to the
internet.

```bash
ssh -L 9119:localhost:9119 ubuntu@<vps>
# then: http://localhost:9119
```

If the dashboard says "disconnected", check `make doctor` and `make logs`.

---

## Telegram pairing

- Bot is created via [@BotFather](https://t.me/BotFather). Disable privacy mode so the
  bot can read DMs.
- `TELEGRAM_BOT_TOKEN` goes into `~/.hermes/.env`.
- The setup wizard captures the operator's Telegram user-id automatically on first DM.
- If Neural goes silent: `make logs | grep -i telegram`. Usually a stale token or the
  operator's user-id wasn't whitelisted.

---

## Backups

- `make backup` produces `~/hermes-backups/hermes-<timestamp>.tar.gz`.
- Cron it nightly:

```
0 3 * * * cd /opt/neuraledge-agent && make backup >>/var/log/hermes-backup.log 2>&1
```

- Ship the tarball off-host (S3 via the n8n backup workflow, or `rsync` to a sibling box).
- **Restore** = extract over `~/.hermes/` on the destination and `make up`. No wizard re-run.

---

## Common incidents

### Agent unresponsive on Telegram

1. `make ps` — all 3 services running?
2. `make logs | tail -100` — recent errors in gateway?
3. `make doctor` — model key, MCP bridge, skin, SOUL all green?
4. Provider rate-limit? Switch via `hermes model` to the fallback provider.

### CORTEX bridge unhealthy

1. `make cortex-status` — which tier is down?
2. `make logs-cortex` — TLS, auth, or network error?
3. If you can't fix CORTEX immediately, flip `CORTEX_MODE=stub` in `~/.hermes/.env` and
   restart cortex-mcp so Neural keeps working on Tier-1 memory.

### Disk filling up

```bash
docker system prune -af
du -sh ~/.hermes/*
# Sessions older than 30 days can be archived if the operator hasn't referenced them.
```

### OOM kills

Visible in `dmesg` and `journalctl -k`. Confirm with `free -h`.

- Short-term: add 2 GB swap (already done by installer if RAM < 6 GB).
- Long-term: resize the instance to t3.large / 8 GB.

### "I can't `make sync-upstream`"

Check the 4 conflicts (README/LICENSE/CONTRIBUTING/.gitignore) are auto-resolving per
`docs/UPGRADING.md`. If a conflict appears on a file NOT in that list, the seam was
violated — find the offending commit and move the change into the NeuralEDGE zone.

---

## Secrets rotation

- LLM API key: edit `~/.hermes/.env` → `make restart`.
- `TELEGRAM_BOT_TOKEN`: same; bot re-pairs on next start.
- `CORTEX_TOKEN`: edit `~/.hermes/.env` → restart cortex-mcp. The bridge holds the
  token; the gateway never sees it.

Never `git add` `.env`. The `.gitignore` excludes it but human attention is the backstop.
