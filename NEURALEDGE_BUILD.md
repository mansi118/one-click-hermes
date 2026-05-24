# NeuralEDGE Agent — Phased Build Spec (v1.1)

**Companion to:** `NEURALEDGE_DESIGN.md` (system design, contracts, reasoning).
**This document:** the *what* and the *order*, plus acceptance criteria per phase.

**v1.1 change vs v1:** rewritten to match the verified upstream contracts
(`v0.14.0` / `v2026.5.16`). Branding plugin replaced by Skin; persona renamed to
SOUL.md; skills restructured to `<slug>/SKILL.md`; compose is now a true overlay;
mcp.json registers cortex-mcp. **Target: 0 core patches.**

Build top-down. Each phase has a single owner, ends with a verifiable check, and is safe to
ship even if later phases are deferred.

---

## Phase 0 — Fork & Baseline

**Goal:** the repo is forkable, the seam is documented, upstream can be pulled in without
collision.

**Tasks**
1. Initialise repo on `main`. Push to deployment repo (e.g. `mansi118/one-click-hermes`).
2. Add upstream remote: `git remote add upstream https://github.com/NousResearch/hermes-agent.git`
3. Pin upstream to a release tag (default `v2026.5.16`).
4. Create the NeuralEDGE-zone directory skeleton:
   ```
   neuraledge/branding/
   neuraledge/skins/
   neuraledge/mcp/cortex-palace/
   neuraledge/config/
   skills/neuraledge/
   docs/
   ```
5. Write `NEURALEDGE_DESIGN.md` (v1.1), `NEURALEDGE_BUILD.md` (this spec),
   `NEURALEDGE_PATCHES.md` (closed verification log + empty patch list).
6. `.gitignore` — union with upstream's at merge time (per the override rule).
7. `LICENSE` (preserves upstream MIT) + `LICENSE-UPSTREAM.md` (attribution).

**Acceptance**
- `git log --oneline -2` shows the scaffold commit and (after merge) the upstream merge.
- The 6 NE-zone directories exist with content.
- `NEURALEDGE_DESIGN.md` and `NEURALEDGE_BUILD.md` cross-link and are version-tagged v1.1.

---

## Phase 1 — Skin + SOUL.md (was: branding plugin)

**Goal:** when Neural starts, it looks and speaks as NeuralEDGE — banner, colors, strings,
persona — using upstream's blessed extension points. Zero Python.

**Tasks**
1. `neuraledge/skins/neuraledge.yaml` — single YAML following the schema in
   `hermes_cli/skin_engine.py`:
   - `name`, `description`
   - `colors:` — banner_*, ui_*, status_bar_*, prompt, response_border, session_*,
     completion_menu_*, voice_status_bg, selection_bg
   - `branding:` — agent_name "Neural", welcome, goodbye, response_label,
     prompt_symbol, help_header
   - `spinner:` — waiting_faces, thinking_faces, thinking_verbs, wings
   - `banner_logo:` — Rich-markup NeuralEDGE wordmark
   - `banner_hero:` — optional minimalist art
2. `neuraledge/branding/SOUL.md` — pure markdown (no YAML frontmatter), persona text
   per Design §3.1.1.
3. `web/themes/neuraledge.css` — dashboard CSS-variable overlay (verified at doctor-time;
   dead code if the dashboard doesn't load it).

**Acceptance**
- `hermes` CLI banner shows NeuralEDGE wordmark in brand colors after `display.skin:
  neuraledge` is set in `~/.hermes/config.yaml`.
- `~/.hermes/SOUL.md` contains the NeuralEDGE soul (not the upstream default).
- `make doctor` reports SOUL.md present and skin loaded.
- **0 core patches** (zero edits to upstream code).

---

## Phase 2 — NeuralEDGE Skills

**Goal:** Neural has NeuralEDGE domain fluency the moment it boots — no learning loop
required.

**Tasks** — write 4 skill files in `skills/neuraledge/<slug>/SKILL.md`. Each follows the
upstream skill frontmatter schema (verified against `skills/apple/apple-notes/SKILL.md`):

```yaml
---
name: <slug>
description: "..."
version: 1.0.0
author: NeuralEDGE
license: MIT
metadata:
  hermes:
    tags: [...]
    related_skills: [...]
---
```

1. `skills/neuraledge/neuraledge-context/SKILL.md` — company, services, NEOS, NeP, ICP, voice.
2. `skills/neuraledge/neos-operations/SKILL.md` — Wings/Halls/Rooms, depth→L0/L1/L2,
   the 5 cortex_* tools, memory routing rule (Design §3.3.4).
3. `skills/neuraledge/deploy-runbook/SKILL.md` — VPS install, AWS SG, SSH tunnel, backup.
4. `skills/neuraledge/client-engagement/SKILL.md` — discovery → audit → build → train.

**Acceptance**
- `hermes skills config` shows all 4 NeuralEDGE skills as enabled.
- A test prompt that references NEOS triggers retrieval of `neuraledge-context` or
  `neos-operations` (verifiable in trace logs).
- Skills survive `make sync-upstream` (live in NE zone, no upstream-name collisions).

---

## Phase 3 — CORTEX-PALACE MCP Bridge

**Goal:** Neural can read/write CORTEX-PALACE through 5 MCP tools. Stub-first; live mode is
a flag flip.

**Tasks**
1. `neuraledge/mcp/cortex-palace/pyproject.toml` — Python package, deps: `mcp[cli]`,
   `pydantic`, `httpx`, `structlog`.
2. `cortex_mcp/__init__.py`, `models.py`, `client.py`, `server.py`, `stub_data.py`,
   `healthcheck.py`.
3. Models: pydantic shapes for each tool's args + return shape (Design §3.3.3).
4. Client: `live` and `stub` modes, timeout, retry, circuit breaker.
5. Server: FastMCP, registers 5 tools — `cortex_recall`, `cortex_remember`,
   `cortex_user_model`, `cortex_search_entities`, `cortex_status`.
6. `Dockerfile` — slim Python 3.13 image, ENTRYPOINT `python -m cortex_mcp.server`,
   HEALTHCHECK via `python -m cortex_mcp.healthcheck`.
7. `tests/test_stub_client.py` — smoke tests against stub mode.
8. `README.md` — env vars, run modes, tool reference.

**Acceptance**
- `CORTEX_MODE=stub docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml
  exec cortex-mcp python -m cortex_mcp.healthcheck` returns exit 0.
- `cortex_status` from inside the gateway returns `{convex/graph/embeddings: ok}` in stub.
- `cortex_recall("anything")` in stub returns ≥1 result with documented shape.
- Circuit breaker fires after N (default 5) consecutive failures in live mode.

---

## Phase 4 — Config & MCP wiring

**Goal:** Three distribution-owned files in `~/.hermes/` make Hermes load the Skin, the
SOUL, the skills, and the cortex-mcp server. Real schema, no guessed keys.

**Tasks**
1. `neuraledge/config/config.defaults.yaml`:
   - `model:` (default + provider + base_url)
   - `terminal:` (docker backend)
   - `display.skin: neuraledge`
   - `skills.disabled: []` (opt-out model)
   - `gateway:`, `worktree: false`
   - **No** `personality:` / `plugins:` / `mcp_servers:` (those don't exist).
2. `neuraledge/config/mcp.json`:
   ```json
   { "mcpServers": { "cortex-mcp": { "transport": "sse",
                                      "url": "http://127.0.0.1:8765/sse" } } }
   ```
3. `neuraledge/config/.env.template` — secrets: LLM key, Telegram token, CORTEX_*,
   N8N_WEBHOOK_URL, HERMES_UID/GID.

**Acceptance**
- Installer copies all three to `~/.hermes/` (idempotent — only if absent).
- `make doctor` reports model configured, skin active, MCP bridge registered.
- Stub-mode tool-call from inside the gateway returns canned data end-to-end.

---

## Phase 5 — Compose overlay & one-click installer

**Goal:** `curl … | bash` on a fresh Ubuntu VPS produces a running Neural in <10 minutes
without the operator typing more than provider/Telegram secrets. Stack uses upstream's
compose extended by ours.

**Tasks**
1. `docker-compose.neuraledge.yml` — overlay format:
   - `gateway:` overridden only to add `depends_on: cortex-mcp`.
   - `cortex-mcp:` new service, `network_mode: host`, binds to `127.0.0.1:8765`.
   - No reimplementation of upstream's `gateway` / `dashboard` services.
2. `neuraledge/install.sh` — 10 idempotent steps per Design §4.2:
   `preflight`, `install_docker`, `ensure_swap`, `fetch_repo` (now also merges upstream
   tag, auto-resolves the 4 override conflicts), `init_state` (seeds SOUL.md, mcp.json,
   skin, skills, config, env), `build_images`, `run_setup_wizard`, `prompt_secrets`,
   `launch`, `verify_and_report`.
3. `Makefile` — `make {install,up,down,logs,doctor,backup,sync-upstream,...}`. All
   compose calls use the overlay (`-f docker-compose.yml -f docker-compose.neuraledge.yml`).

**Acceptance**
- Re-running `install.sh` on an already-installed host is a no-op.
- `make doctor` green on a fresh VPS within 10 minutes of `install.sh` (assuming
  LLM key + Telegram token at hand).
- `ss -tlnp` shows ports `9119` (dashboard) and `8765` (cortex-mcp) bound to `127.0.0.1`
  only. No `0.0.0.0` bindings.

---

## Phase 6 — Polish & docs

**Goal:** the project is shippable — a new operator can read one README and one runbook,
and an engineer can sync upstream without paging the original author.

**Tasks**
1. `README.md` (NeuralEDGE-branded): install one-liner, dashboard tunnel recipe,
   Telegram pairing, links to design + build docs.
2. `LICENSE` (upstream MIT, preserved) + `LICENSE-UPSTREAM.md`.
3. `CONTRIBUTING.md` — fork sync workflow, the 4-conflict rule, override policy.
4. `docs/RUNBOOK.md` — operations: rotating keys, swapping providers, restoring from
   backup, reading logs, switching CORTEX_MODE.
5. `docs/UPGRADING.md` — `make sync-upstream`, the test checklist.
6. Tag `ne-v0.14.0-1` (Hermes upstream `v0.14.0` / `v2026.5.16`, NE iteration `1`).

**Acceptance**
- README install one-liner copy-pastes and works.
- A new engineer can `make sync-upstream UPSTREAM_TAG=…` without consulting the author.
- All 6 phase acceptances pass.

---

## Test checklist (per phase + before each release)

```
[ ] hermes doctor — all green
[ ] cortex_status — convex/graph/embeddings status correct for current CORTEX_MODE
[ ] Telegram round-trip — send "ping", receive "pong" from Neural
[ ] Dashboard — loads via SSH tunnel, themed (skin: neuraledge), no console errors
[ ] Skills loaded — `hermes skills config` shows 4 NE skills enabled
[ ] Persona — system prompt matches ~/.hermes/SOUL.md content
[ ] Memory — Tier-1 recall of last session works; Tier-2 cortex_recall returns ≥1 hit
[ ] Ports — no agent ports listening on 0.0.0.0 (ss -tlnp)
[ ] Logs — secrets redacted in `make logs`
[ ] Upstream sync — `git merge` from pinned tag had exactly 4 conflicts (the override set)
```

---

## What to do when a phase fails its acceptance

1. **Do not** force-mark the task completed.
2. Open `NEURALEDGE_PATCHES.md` and check whether the failure is because Hermes doesn't
   expose the extension point you assumed. If yes, re-do the verification pass against
   the pinned tag — *don't* add a core patch on the first failure.
3. If a patch is genuinely needed, log it per the template and apply it. Each patch
   makes future merges slightly more expensive; treat the budget seriously.
4. Re-run the acceptance. Only then update the task.
