# NeuralEDGE Agent — Operations Runbook

The day-2 guide. Skill version of the same content (loaded into Neural) lives at
`skills/neuraledge/deploy-runbook.md`. This file is the human-readable expanded form.

---

## Layout on the VPS

| Path | Contents |
|---|---|
| `/opt/neuraledge-agent` | Git checkout of the `neuraledge` branch |
| `~/.hermes/config.yaml` | Active config (seeded from `neuraledge/config/config.defaults.yaml`) |
| `~/.hermes/.env` | Secrets, mode `600` (seeded from `.env.template`) |
| `~/.hermes/sessions/` | Tier-1 session memory + Honcho user model |
| `~/.hermes/skills/` | Skills *learned at runtime*. Seed skills live in repo. |
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
| Follow agent logs | `make logs` |
| Follow MCP bridge logs | `make logs-cortex` |
| Container status | `make ps` |
| Self-check | `make doctor` |
| CORTEX health | `make cortex-status` |
| Backup | `make backup` |
| Drop into agent shell | `make shell` |

All `make` targets are thin wrappers around `docker compose -f
docker-compose.neuraledge.yml …`.

---

## Switching LLM provider

Edit `~/.hermes/.env` for the key, and `~/.hermes/config.yaml` `provider:` block for the
model. Then `make restart`.

```yaml
# ~/.hermes/config.yaml
provider:
  default: anthropic
  anthropic:
    model: claude-sonnet-4-6
```

For a one-off switch without editing files:

```bash
docker compose -f docker-compose.neuraledge.yml exec hermes hermes model anthropic/claude-sonnet-4-6
```

---

## Switching CORTEX-PALACE mode

**Stub → live:**

```bash
# Edit ~/.hermes/.env
CORTEX_MODE=live
CORTEX_ENDPOINT=https://cortex.neos.internal
CORTEX_TOKEN=<bearer>

docker compose -f docker-compose.neuraledge.yml restart cortex-mcp
make cortex-status   # expect mode=live, all tiers ok
```

**Live → stub** (e.g. for an outage drill or local dev):

```bash
# Edit ~/.hermes/.env: CORTEX_MODE=stub
docker compose -f docker-compose.neuraledge.yml restart cortex-mcp
```

Neural detects the mode automatically — no agent restart needed for tool behaviour
change; new tool calls hit the updated client immediately.

---

## Dashboard access

Bound to `127.0.0.1` on the VPS. Use an SSH local-forward — never expose to the
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

1. `make ps` — both services running?
2. `make logs | tail -100` — recent errors?
3. `make doctor` — provider key, MCP bridge, skills load.
4. Provider rate-limit? Switch via `hermes model` to the fallback provider.

### CORTEX bridge unhealthy

1. `make cortex-status` — which tier is down?
2. `make logs-cortex` — TLS, auth, or network error?
3. If you can't fix CORTEX immediately, flip `CORTEX_MODE=stub` and restart `cortex-mcp`
   so Neural keeps working on Tier-1 memory.

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

Check `NEURALEDGE_PATCHES.md`. If empty, the conflict is unexpected — something
violated the fork seam. Find the offending commit in the NeuralEDGE branch and move the
change out of the upstream zone before re-attempting the merge.

---

## Secrets rotation

- `LLM_API_KEY`: edit `~/.hermes/.env` → `make restart`.
- `TELEGRAM_BOT_TOKEN`: same; bot re-pairs on next start.
- `CORTEX_TOKEN`: edit `~/.hermes/.env` → `docker compose restart cortex-mcp`. The
  bridge holds the token; Hermes never sees it.

Never `git add` `.env`. The `.gitignore` excludes it but human attention is the backstop.
