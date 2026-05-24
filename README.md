# NeuralEDGE Agent — Neural

> A self-hosted, 24/7 executive AI assistant for the NeuralEDGE operator.
> Branded fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent),
> wired into the NEOS / CORTEX-PALACE knowledge system.

```
  N E U R A L
  ─────────────
  Run your business on signal, not chaos.
```

---

## What this is

Neural is a NeuralEDGE-branded distribution of NousResearch's Hermes Agent. It inherits
the full Hermes feature set — learning loop, 40+ tools, 7 terminal backends,
multi-platform gateway, cron, MCP — and adds:

- **NeuralEDGE persona** (`NEURAL.md`) — voice, identity, conduct.
- **NeuralEDGE skills** — company, NEOS operations, deploy runbook, engagement workflow.
- **CORTEX-PALACE MCP bridge** — durable institutional memory via NEOS Convex/FalkorDB.
- **One-click installer** — `curl | bash` on a fresh Ubuntu VPS.
- **Branded dashboard** — same Hermes web UI, NeuralEDGE palette and typography.

The agent runs on a single VPS, talks to the operator via Telegram (and CLI/dashboard
when SSH'd in), and never exposes itself to the public internet.

---

## Quick install

```bash
curl -fsSL https://get.neuraledge.in/agent | bash
```

The installer is idempotent and walks the operator through:

1. Docker + swap
2. Repo fetch
3. Image build
4. Hermes setup wizard (provider + Telegram pairing)
5. CORTEX-PALACE secrets (or leave in stub mode)
6. Launch and verify

Full prereqs and tunables: `skills/neuraledge/deploy-runbook.md`.

---

## Access

| Channel | How |
|---|---|
| **Telegram** | Pair a bot in the setup wizard; DM the bot. |
| **Dashboard** | SSH tunnel: `ssh -L 9119:localhost:9119 user@vps` → `http://localhost:9119` |
| **CLI** | SSH to the host, then `docker compose exec hermes hermes` |

The agent's ports (`8642`/`9119`) bind to `127.0.0.1` only. SSH (port 22) should be the
only inbound rule in the AWS Security Group, restricted to the operator's IP.

---

## Day-2 operations

```bash
make up            # start
make down          # stop
make logs          # follow hermes logs
make doctor        # self-check
make backup        # tar ~/.hermes
make sync-upstream # pull NousResearch, merge into neuraledge branch
```

See `docs/RUNBOOK.md` for the full operations guide.

---

## Architecture in one diagram

```
                          ┌──────────── VPS (Docker host) ────────────┐
  Operator ──Telegram──▶   │  ┌─────────────────┐   ┌──────────────┐   │
  Operator ──SSH/CLI──▶    │  │  hermes (Neural)│◀─▶│ cortex-mcp   │   │──▶ CORTEX-PALACE
  Operator ──SSH tunnel─▶  │  │  gateway+dash   │   │ (MCP bridge) │   │    (Convex/Falkor)
                          │  └────────┬────────┘   └──────────────┘   │
                          │           │ outbound only                  │──▶ LLM provider
                          │           └──────────────────────────────  │──▶ n8n.neuraledge.in
                          │     volume: ~/.hermes (single source state) │
                          └─────────────────────────────────────────────┘
```

Two-tier memory:
- **Tier 1** — native Hermes session memory + Honcho user model. Fast working memory.
- **Tier 2** — CORTEX-PALACE via `cortex_*` MCP tools. Durable institutional knowledge.

Routing rule: see `skills/neuraledge/neos-operations.md`.

---

## Project layout

```
.
├── NEURALEDGE_DESIGN.md    System design and contracts
├── NEURALEDGE_BUILD.md     Phased build spec with acceptance checks
├── NEURALEDGE_PATCHES.md   Log of any upstream core patches (target: 0–2)
├── neuraledge/
│   ├── branding/           Banner, theme tokens, strings, NEURAL.md persona
│   ├── config/             config.defaults.yaml + .env.template
│   ├── install.sh          One-click installer
│   └── mcp/cortex-palace/  CORTEX-PALACE MCP bridge (FastMCP, Python)
├── plugins/ne_branding/    Hermes plugin that applies the branding overlay
├── skills/neuraledge/      4 pinned NeuralEDGE seed skills
├── web/themes/             Dashboard theme overlay (CSS variables only)
├── Dockerfile.neuraledge   Extends upstream Dockerfile; COPYs the overlay
├── docker-compose.neuraledge.yml   2-service stack (hermes + cortex-mcp)
├── Makefile                Lifecycle, observability, backup, upstream sync
└── LICENSE / LICENSE-UPSTREAM.md
```

Everything in `neuraledge/`, `skills/neuraledge/`, `plugins/ne_branding/`,
`web/themes/neuraledge.css`, `Dockerfile.neuraledge`, and
`docker-compose.neuraledge.yml` is **NeuralEDGE-zone**. Upstream Hermes lives
everywhere else and is preserved unmodified — see `NEURALEDGE_PATCHES.md`.

---

## Upstream sync

```bash
make sync-upstream   # git pull upstream main && merge into neuraledge
make build           # rebuild images
make doctor          # verify
```

Conflicts are expected to be zero — the NeuralEDGE zone is intentionally non-overlapping
with upstream. The only risk is the patches logged in `NEURALEDGE_PATCHES.md` (target:
none). See `docs/UPGRADING.md` for the full release checklist.

---

## Reading order

1. `NEURALEDGE_DESIGN.md` — the system contract.
2. `NEURALEDGE_BUILD.md` — phases and acceptance.
3. `skills/neuraledge/` — what Neural knows.
4. `neuraledge/mcp/cortex-palace/README.md` — the bridge.
5. `docs/RUNBOOK.md` — keeping it healthy.

---

## License

MIT — preserves upstream Hermes Agent (NousResearch) attribution. See `LICENSE` and
`LICENSE-UPSTREAM.md`.

NeuralEDGE Agent is **not** affiliated with NousResearch beyond this MIT-licensed fork.
