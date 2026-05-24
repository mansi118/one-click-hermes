# NeuralEDGE Agent — Phased Build Spec

**Companion to:** `NEURALEDGE_DESIGN.md` (system design, contracts, reasoning).
**This document:** the *what* and the *order*, plus acceptance criteria per phase.

Build top-down. Each phase has a single owner, ends with a verifiable check, and is safe to
ship even if later phases are deferred.

---

## Phase 0 — Fork & Baseline

**Goal:** the repo is forkable, the seam is documented, upstream can be pulled in without
collision. No agent code yet.

**Tasks**
1. Initialise repo on the `neuraledge` branch. `main` mirrors NousResearch upstream
   verbatim; never commit NeuralEDGE files to `main`.
2. Add the upstream remote: `git remote add upstream https://github.com/NousResearch/hermes-agent.git`
   (URL confirmed at fork time).
3. Create the NeuralEDGE zone directory skeleton:
   ```
   neuraledge/branding/persona/
   neuraledge/mcp/cortex-palace/
   neuraledge/config/
   skills/neuraledge/
   plugins/ne_branding/
   ```
4. Write `NEURALEDGE_DESIGN.md` (this design) and `NEURALEDGE_BUILD.md` (this spec).
5. Write `NEURALEDGE_PATCHES.md` — even if empty, the file lives so any future core patch is
   logged the moment it's added.
6. `.gitignore` — exclude `~/.hermes/`, `*.env` (except `.env.template`), `__pycache__`,
   `node_modules`, `dist`, `*.log`, MCP bridge venv.
7. `LICENSE` — preserve upstream MIT; `LICENSE-NEURALEDGE` for NeuralEDGE additions if needed.

**Acceptance**
- `git log --oneline --all` shows `main` tracking upstream and `neuraledge` carrying only
  meta/skeleton commits.
- The 6 NeuralEDGE-zone directories exist (may contain `.gitkeep`).
- `NEURALEDGE_DESIGN.md` and `NEURALEDGE_BUILD.md` are committed and cross-link each other.

---

## Phase 1 — Branding Subsystem

**Goal:** when Neural starts, it looks and speaks as NeuralEDGE — banner, theme tokens,
strings, persona — without any core Hermes edits beyond plugin registration.

**Tasks**
1. `neuraledge/branding/banner.txt` — ASCII art with the NeuralEDGE wordmark + tagline
   "Run your business on signal, not chaos."
2. `neuraledge/branding/theme.toml` — color tokens (navy/teal/ice/slate), font stack
   (Space Grotesk / DM Sans / JetBrains Mono).
3. `neuraledge/branding/strings.toml` — display string overrides keyed by upstream string id.
4. `neuraledge/branding/persona/NEURAL.md` — full persona prompt per Design §3.1.1.
5. `plugins/ne_branding/plugin.py` — Hermes plugin entrypoint; reads the three TOML/text
   files and patches the registry hooks Hermes exposes for banner/theme/strings.
6. `plugins/ne_branding/plugin.toml` — plugin manifest (name, version, entrypoint).
7. Web theme overlay — `web/themes/neuraledge.css` with CSS custom-properties matching
   `theme.toml`. Loaded by the config flag `dashboard.theme: neuraledge`.

**Acceptance**
- `hermes --version` prints NeuralEDGE banner.
- Personality `neural` is selectable in CLI/setup wizard and the loaded system prompt
  matches `NEURAL.md`.
- Dashboard, when launched, renders with NeuralEDGE palette.
- Phase 1 made **0** core-Hermes edits (or **1** edit logged in `NEURALEDGE_PATCHES.md`).

---

## Phase 2 — NeuralEDGE Skills

**Goal:** Neural has NeuralEDGE domain fluency the moment it boots — no learning loop
required.

**Tasks** — write the 4 skill files in `skills/neuraledge/`. Each must use the agentskills.io
frontmatter Hermes already parses:
```yaml
---
name: ...
description: when this skill is relevant (Hermes uses this to retrieve)
pinned: true
tags: [...]
---
```

1. `neuraledge-context.md` — company facts: three services, NEOS, NeP, ICP, team, voice.
2. `neos-operations.md` — Wings/Halls/Rooms vocabulary, depth-to-L0/L1/L2 mapping,
   memory routing rule from Design §3.3.4.
3. `deploy-runbook.md` — VPS install, AWS SG reminders, SSH tunnel for dashboard, backup.
4. `client-engagement.md` — discovery → audit → build → train workflow patterns.

**Acceptance**
- `hermes skills list` shows the 4 skills as pinned.
- A test prompt ("what is NEOS?") loads `neuraledge-context.md` into context (verifiable
  in trace logs).
- A test prompt ("how do I check long-term memory health?") loads `neos-operations.md`.

---

## Phase 3 — CORTEX-PALACE MCP Bridge

**Goal:** Neural can read/write CORTEX-PALACE through 5 MCP tools. Stub-first; live mode is
a flag flip.

**Tasks**
1. `neuraledge/mcp/cortex-palace/pyproject.toml` — Python package, deps: `mcp[cli]`,
   `pydantic`, `httpx`, `pyyaml`.
2. `neuraledge/mcp/cortex-palace/cortex_mcp/__init__.py` — package init.
3. `neuraledge/mcp/cortex-palace/cortex_mcp/models.py` — pydantic models for each tool's
   args + return shape, per Design §3.3.3.
4. `neuraledge/mcp/cortex-palace/cortex_mcp/client.py` — `CortexClient` with `live` and
   `stub` modes, timeout, retry, circuit breaker.
5. `neuraledge/mcp/cortex-palace/cortex_mcp/server.py` — FastMCP server registering the 5
   tools (`cortex_recall`, `cortex_remember`, `cortex_user_model`,
   `cortex_search_entities`, `cortex_status`).
6. `neuraledge/mcp/cortex-palace/cortex_mcp/stub_data.py` — canned NeuralEDGE-shaped
   responses so stub mode is realistic.
7. `neuraledge/mcp/cortex-palace/Dockerfile` — slim Python 3.13 image; entrypoint
   `python -m cortex_mcp.server`.
8. `neuraledge/mcp/cortex-palace/README.md` — env vars, run modes, tool reference.

**Acceptance**
- `CORTEX_MODE=stub python -m cortex_mcp.server` runs cleanly; MCP inspector can list
  the 5 tools.
- `cortex_status()` in stub mode returns `{convex: ok, graph: ok, embeddings: ok}` with
  a fake latency.
- `cortex_recall("test query")` in stub mode returns ≥1 result with the documented shape.
- Circuit breaker fires after N (default 5) consecutive failures and emits
  `degraded: true`.

---

## Phase 4 — Config & Infra Wiring

**Goal:** the one configuration file makes Hermes load the persona, the skills, the
branding plugin, and the MCP bridge — no per-install hand-editing.

**Tasks**
1. `neuraledge/config/config.defaults.yaml`:
   - `personality: neural`
   - `plugins.enabled: [ne_branding]`
   - `skills.paths: [skills/neuraledge]`
   - `mcp_servers.cortex-mcp` block (transport, env passthrough)
   - `mcp_servers.n8n` block (commented until URL confirmed)
   - `provider.default: openrouter` (changeable)
   - `dashboard.theme: neuraledge`
   - `gateway.bind: 127.0.0.1`
2. `neuraledge/config/.env.template`:
   - `LLM_API_KEY=`
   - `TELEGRAM_BOT_TOKEN=`
   - `CORTEX_MODE=stub`
   - `CORTEX_ENDPOINT=`
   - `CORTEX_TOKEN=`
   - `N8N_WEBHOOK_URL=`
   - `HERMES_UID=1000`
   - `HERMES_GID=1000`
3. n8n integration note in `skills/neuraledge/neos-operations.md` (or a sibling
   `n8n-workflows.md` once endpoints exist).

**Acceptance**
- `cp neuraledge/config/config.defaults.yaml ~/.hermes/config.yaml` + envs set → `hermes
  doctor` reports persona, skills path, and MCP bridge all green.
- Stub-mode tool-call from inside the agent loop returns canned data end-to-end.

---

## Phase 5 — Docker Compose & One-Click Installer

**Goal:** `curl … | bash` on a fresh Ubuntu VPS produces a running Neural in <10 minutes
without the operator typing more than provider/Telegram secrets.

**Tasks**
1. `Dockerfile.neuraledge` — extends upstream `Dockerfile`; `COPY`s `neuraledge/branding/`,
   `skills/neuraledge/`, `plugins/ne_branding/`, `neuraledge/config/config.defaults.yaml`.
2. `docker-compose.neuraledge.yml` — 2 services (`hermes`, `cortex-mcp`) on
   `hermes-net` bridge per Design §4.1. Ports `127.0.0.1:8642`/`127.0.0.1:9119`. Volume
   `~/.hermes:/opt/data`. `restart: unless-stopped`.
3. `neuraledge/install.sh` — 10-step idempotent script per Design §4.2. Functions:
   `preflight`, `install_docker`, `ensure_swap`, `fetch_repo`, `init_state`, `build_images`,
   `run_setup_wizard`, `prompt_secrets`, `launch`, `verify_and_report`.
4. `Makefile` — `make install`, `make up`, `make down`, `make logs`, `make doctor`,
   `make backup`, `make sync-upstream`.

**Acceptance**
- Re-running `install.sh` on an already-installed host is a no-op (each function returns 0
  without state change).
- `make doctor` green on a fresh VPS within 10 minutes of running `install.sh` (assuming
  LLM key + Telegram token at hand).
- Ports `0.0.0.0:8642/9119` are **not** listening (verify with `ss -tlnp`).

---

## Phase 6 — Polish & Docs

**Goal:** the project is shippable — a new operator can read one README and one runbook and
get going; an engineer can sync upstream without paging the original author.

**Tasks**
1. `README.md` (NeuralEDGE-branded): what Neural is, install one-liner, dashboard tunnel
   recipe, Telegram pairing, links to design + build docs.
2. `LICENSE` (upstream MIT, preserved) + `LICENSE-UPSTREAM.md` (attribution).
3. `CONTRIBUTING.md` — fork sync workflow (clone, set upstream, `make sync-upstream`,
   resolve via `NEURALEDGE_PATCHES.md` if a core patch was added).
4. `docs/RUNBOOK.md` — operations: rotating keys, swapping providers, restoring from
   backup, reading logs, switching CORTEX_MODE.
5. `docs/UPGRADING.md` — how to run `make sync-upstream` and the test checklist.
6. Tag `ne-v0.14.0-1` (Hermes upstream `v0.14.0`, NeuralEDGE iteration `1`).

**Acceptance**
- README install one-liner copy-pastes and works.
- A new engineer can `git pull upstream main && git merge` without consulting the author.
- All 6 phase acceptances pass.

---

## Test checklist (per phase + before each release)

```
[ ] hermes doctor — all green
[ ] cortex_status — convex/graph/embeddings status correct for current mode
[ ] Telegram round-trip — send "ping", receive "pong" from Neural
[ ] Dashboard — loads via SSH tunnel, themed, no console errors
[ ] Skills loaded — `hermes skills list` shows 4 pinned NeuralEDGE skills
[ ] Persona — system prompt includes NEURAL.md content
[ ] Memory — Tier-1 recall of last session works; Tier-2 stub-call succeeds
[ ] Ports — no agent ports listening on 0.0.0.0
[ ] Logs — secrets redacted in `docker compose logs hermes`
[ ] Upstream sync — `git merge` from `main` had ≤ #core-patches conflicts
```

---

## What to do when a phase fails its acceptance

1. **Do not** force-mark the task completed.
2. Open `NEURALEDGE_PATCHES.md` and check if the failure is because Hermes doesn't expose
   the hook you needed. If yes, add the smallest possible core patch and log it.
3. If the failure is in NeuralEDGE-zone code, fix it in the zone; phases must remain
   non-overlapping with upstream.
4. Re-run the acceptance. Only then update the task.
