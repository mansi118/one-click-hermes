# NeuralEDGE Agent — Neural

> A self-hosted, 24/7 executive AI assistant for the NeuralEDGE operator.
> Distribution overlay on [Hermes Agent](https://github.com/NousResearch/hermes-agent)
> `v2026.5.16` (= `v0.14.0`), wired into the NEOS / CORTEX-PALACE knowledge system.

```
  N E U R A L
  ─────────────
  Run your business on signal, not chaos.
```

---

## What this is

Neural is a NeuralEDGE-branded distribution of NousResearch's Hermes Agent. It inherits
the full Hermes feature set — learning loop, 40+ tools, 7 terminal backends,
multi-platform gateway, cron, MCP — and adds five upstream-blessed extensions:

- **Skin** (`~/.hermes/skins/neuraledge.yaml`) — banner, colors, branding strings.
- **SOUL.md** (`~/.hermes/SOUL.md`) — Neural's persona: voice, identity, conduct.
- **Skills** (`skills/neuraledge/<slug>/SKILL.md` × 4) — company, NEOS operations,
  deploy runbook, engagement workflow.
- **CORTEX-PALACE MCP bridge** (registered under `mcp_servers:` in `~/.hermes/config.yaml`,
  served by the `cortex-mcp` sidecar) — durable institutional memory via NEOS Convex / FalkorDB.
- **One-click installer** — `curl | bash` on a fresh Ubuntu VPS.

Zero core patches to upstream. All five extensions are official extension points; upstream
merges stay frictionless forever.

The agent runs on a single VPS, talks to the operator via Telegram (and CLI/dashboard
when SSH'd in), and never exposes itself to the public internet.

---

## Quick install

```bash
curl -fsSL https://get.neuraledge.in/agent | bash
```

The installer is idempotent and walks the operator through:

1. Docker + swap
2. Fetch this repo + upstream Hermes pinned to `v2026.5.16`
3. Seed `~/.hermes/{config.yaml, SOUL.md, skins/neuraledge.yaml, skills/neuraledge/, .env}`
4. Build the `hermes-agent` (upstream) + `cortex-mcp` (NeuralEDGE) images
5. Hermes setup wizard (model + Telegram pairing)
6. Optional CORTEX-PALACE secrets (stub mode is the default)
7. Launch with `docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml up -d`
8. `make doctor` — green is the gate

Full prereqs and tunables: `skills/neuraledge/deploy-runbook/SKILL.md`.

---

## Access

| Channel | How |
|---|---|
| **Telegram** | Pair a bot in the setup wizard; DM the bot. |
| **Dashboard** | SSH tunnel: `ssh -L 9119:localhost:9119 user@vps` → `http://localhost:9119` |
| **CLI** | SSH to the host, then `make shell` (or `docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml exec gateway hermes`) |

The gateway and dashboard use `network_mode: host` and bind to `127.0.0.1` only. SSH
(port 22) should be the only inbound rule in the AWS Security Group, restricted to the
operator's IP.

---

## Day-2 operations

```bash
make up            # start gateway + dashboard + cortex-mcp
make down          # stop
make logs          # follow gateway logs
make doctor        # the only green/red signal that counts
make backup        # tar ~/.hermes
make sync-upstream # pull a newer Hermes release tag, merge into our branch
```

See `docs/RUNBOOK.md` for the full operations guide.

---

## Architecture

```
                          ┌──────────── VPS (Docker host, network_mode: host) ──┐
  Operator ──Telegram──▶   │  ┌───────────────────┐  ┌──────────────┐             │
  Operator ──SSH/CLI──▶    │  │  gateway          │  │ cortex-mcp   │             │──▶ CORTEX-PALACE
  Operator ──SSH tunnel─▶  │  │  (hermes-agent)   │◀▶│ 127.0.0.1:8765│             │   (NEOS Convex)
                          │  └──┬────────────────┘  └──────────────┘             │
                          │     │      ┌──────────────────┐                      │──▶ LLM provider
                          │     │      │  dashboard       │ ←ssh tunnel→         │──▶ n8n.neuraledge.in
                          │     │      │  127.0.0.1:9119  │                      │
                          │     │      └──────────────────┘                      │
                          │     └─ shared volume: ~/.hermes:/opt/data            │
                          │        (config.yaml — incl. mcp_servers, SOUL.md,     │
                          │         skills/, sessions/, .env)                     │
                          └─────────────────────────────────────────────────────┘
```

Two-tier memory:
- **Tier 1** — native Hermes session memory + Honcho user model. Fast working memory.
- **Tier 2** — CORTEX-PALACE via `cortex_*` MCP tools (5 tools). Durable institutional memory.

Routing rule: see `skills/neuraledge/neos-operations/SKILL.md`.

---

## Project layout

```
.
├── NEURALEDGE_DESIGN.md    System design and contracts (v1.1)
├── NEURALEDGE_BUILD.md     Phased build spec with acceptance checks
├── NEURALEDGE_PATCHES.md   Core-patch log (target: 0) + verification log (closed)
├── neuraledge/
│   ├── branding/SOUL.md    Neural's persona (seeded to ~/.hermes/SOUL.md)
│   ├── skins/              NeuralEDGE Skin (single YAML; seeded to ~/.hermes/skins/)
│   ├── config/             config.defaults.yaml + .env.template
│   ├── install.sh          One-click installer (idempotent, 10 steps)
│   └── mcp/cortex-palace/  CORTEX-PALACE MCP bridge (FastMCP, Python, stub-first)
├── skills/neuraledge/      4 seed skills, each as <slug>/SKILL.md
├── web/themes/             Dashboard CSS overlay (verified at doctor-time)
├── docker-compose.neuraledge.yml   Overlay — adds cortex-mcp service
├── Makefile                Lifecycle + ops + upstream sync targets
└── LICENSE / LICENSE-UPSTREAM.md
```

Everything under `neuraledge/`, `skills/neuraledge/`, `web/themes/neuraledge.css`, and
`docker-compose.neuraledge.yml` is the **NeuralEDGE zone**. Top-level meta files
(README, LICENSE, CONTRIBUTING, .gitignore, Makefile) override upstream at merge time
per the rule in `NEURALEDGE_PATCHES.md`.

---

## Upstream sync

```bash
make sync-upstream UPSTREAM_TAG=v2026.5.16   # or whichever release tag you pin to
make build
make doctor
```

Conflicts are limited to the 4 top-level meta files (README/LICENSE/CONTRIBUTING/.gitignore)
with documented resolution; the install.sh auto-resolves them. The NeuralEDGE-zone files
never collide. See `docs/UPGRADING.md` for the full release checklist.

---

## Reading order

1. `NEURALEDGE_DESIGN.md` — the system contract.
2. `NEURALEDGE_BUILD.md` — phases and acceptance.
3. `skills/neuraledge/*/SKILL.md` — what Neural knows.
4. `neuraledge/mcp/cortex-palace/README.md` — the MCP bridge.
5. `docs/RUNBOOK.md` — keeping it healthy.

---

## License

MIT — preserves upstream Hermes Agent (NousResearch) attribution. See `LICENSE` and
`LICENSE-UPSTREAM.md`.

NeuralEDGE Agent is **not** affiliated with NousResearch beyond this MIT-licensed distribution
overlay.
