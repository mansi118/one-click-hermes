# NeuralEDGE Agent ("Neural") — End-to-End Technical System Design

**Status:** Design v1 · **Base:** Hermes Agent v0.14.0 (NousResearch, MIT) · **Codename:** Neural
**Owner:** ML / NeuralEDGE · **Companion doc:** `NEURALEDGE_BUILD.md` (phased build spec)

This document is the technical design behind the build spec. The build spec says *what to
build and in what order*; this says *how the system is shaped, what the contracts are, and
how the pieces talk*. Read both.

---

## 1. System Context

### 1.1 What this is

A forked, NeuralEDGE-branded distribution of Hermes Agent that runs as a self-hosted,
24/7 autonomous assistant ("Neural"). It inherits the entire Hermes feature set — learning
loop, 40+ tools, 7 terminal backends, multi-platform gateway, cron, MCP — and adds a
NeuralEDGE identity plus a bridge into the NEOS / CORTEX-PALACE knowledge system. It deploys
to any VPS with one command.

### 1.2 Actors

| Actor | Role |
|---|---|
| **Operator** (ML / "Yatharth Sir") | Talks to Neural via Telegram / CLI / dashboard. The agent builds a model of this person. |
| **Neural** (the agent) | The Hermes agent loop, branded + persona'd as NeuralEDGE's executive assistant. |
| **CORTEX-PALACE** | Existing NEOS long-term memory system (Convex + FalkorDB/Graphiti). External to this repo — Neural *connects* to it. |
| **NeuralEDGE infra** | `n8n.neuraledge.in` (automations), `matrix.neuraledge.in` (comms), AWS EC2 `ap-south-1`. |
| **Upstream** | NousResearch — ships new Hermes releases we merge in. |

### 1.3 System boundary

```
                          ┌──────────── VPS (Docker host) ────────────┐
  Operator ──Telegram──▶   │  ┌─────────────────┐   ┌──────────────┐   │
  Operator ──SSH/CLI──▶    │  │  hermes (Neural)│◀─▶│ cortex-mcp   │   │──▶ CORTEX-PALACE
  Operator ──SSH tunnel─▶  │  │  gateway+dash   │   │ (bridge)     │   │    (Convex/Falkor)
                          │  └────────┬────────┘   └──────────────┘   │
                          │           │ outbound only                  │──▶ LLM provider
                          │           └──────────────────────────────  │──▶ n8n.neuraledge.in
                          │     volume: ~/.hermes (single source state) │
                          └─────────────────────────────────────────────┘
```

Two things cross the boundary inbound: SSH (port 22, operator IP only). Everything else —
Telegram polling, LLM calls, CORTEX-PALACE, n8n — is **outbound**. The agent is never
directly addressable from the internet.

---

## 2. Architectural Principle: The Fork Seam

The single most important design decision. The codebase is split into two zones with a hard
seam between them:

```
  UPSTREAM ZONE  (never edit)              NEURALEDGE ZONE  (all custom work)
  ─────────────────────────                ────────────────────────────────
  agent/        gateway/                   neuraledge/branding/
  providers/    hermes_*.py                neuraledge/mcp/cortex-palace/
  cli.py        tools/  cron/              neuraledge/config/
  web/ (structure)                         neuraledge/install.sh
  Dockerfile (base)                        skills/neuraledge/
                                           docker-compose.neuraledge.yml
```

**The seam is enforced by 4 mechanisms:**

1. **Plugin system** — Hermes loads plugins from `plugins/`. Branding, custom tools, and
   startup hooks register here. A plugin is the preferred attach point for any behaviour change.
2. **Skills directory** — pure Markdown, zero code. Company knowledge attaches here.
3. **Config layering** — `~/.hermes/config.yaml` carries all defaults (provider, persona,
   MCP servers, skill paths). Nothing is hardcoded that config can carry.
4. **MCP** — external capability (CORTEX-PALACE, n8n) attaches as MCP servers, not as code
   inside the agent.

Anything that cannot be done through these 4 is a **core patch** — minimal, isolated, logged
in `NEURALEDGE_PATCHES.md`. Target: ≤2 core patches total, each ≤10 lines. The merge cost of
upstream releases is proportional to core-patch surface area; keep it near zero.

---

## 3. Component Design

### 3.1 Branding subsystem (`neuraledge/branding/` + branding plugin)

**Responsibility:** make the running agent look and speak as NeuralEDGE without restructuring
Hermes UI code.

**Files:**
- `banner.txt` — ASCII banner for CLI startup.
- `banner.png` — dashboard/README banner asset.
- `theme.toml` — color tokens: `navy=#132F48 teal=#13C5B3 ice=#EFF4F9 slate=#4C5A6A`;
  fonts `Space Grotesk / DM Sans / JetBrains Mono`.
- `strings.toml` — display-string overrides (`product_name`, `tagline`, `support_url`,
  help-footer text). Key = upstream string id, value = NeuralEDGE replacement.
- `persona/NEURAL.md` — the SOUL/persona file (see 3.1.1).

**Mechanism — branding plugin** (`plugins/ne_branding/`): a Hermes plugin that on load reads
`theme.toml` + `strings.toml` and applies overrides through whatever hook Hermes exposes for
banner/strings. Plugins are the upstream-blessed extension point, so this survives merges.

*Contingency:* if the CLI banner is hardcoded with no hook, the allowed core patch is a single
conditional in the CLI entrypoint — "if `neuraledge/branding/banner.txt` exists, use it" —
logged in `NEURALEDGE_PATCHES.md`.

**Dashboard (`web/`, TypeScript):** retheme via CSS-variable / theme-token file only. Swap
color tokens, font imports, logo asset. No component restructuring — that would make every
upstream `web/` change a conflict.

#### 3.1.1 NEURAL.md persona contract

The persona file makes the agent *be* Neural. Content requirements:

- **Identity:** "You are Neural, NeuralEDGE's AI executive assistant." Runs on the NeuralEDGE
  stack (OpenClaw lineage, Hermes runtime).
- **Operator address:** "Yatharth Sir" by default; "ML" in casual context.
- **Voice:** direct, concise, no filler, no flattery. Hindi/Hinglish acceptable when the
  operator uses it.
- **Capability awareness:** knows it has CORTEX-PALACE (long-term memory) and n8n (automation)
  available as tools, and *when* to reach for each (see 3.3.4).
- **Boundaries:** does not fabricate NEOS/client facts — queries CORTEX-PALACE instead.

Loaded as the default personality via config (`personality: neural`), so no code change.

### 3.2 Skills subsystem (`skills/neuraledge/`)

**Responsibility:** give Neural NeuralEDGE domain fluency and standard procedures as
procedural memory. Pure Markdown (agentskills.io frontmatter format Hermes already parses).

| Skill file | Purpose | `pinned` |
|---|---|---|
| `neuraledge-context.md` | Company facts: 3 services (Audit/Digital Employee/Training), NEOS, NeP ecosystem, team, ICP, brand voice | yes |
| `neos-operations.md` | How/when to query CORTEX-PALACE; Wings/Halls/Rooms vocabulary; L0/L1/L2 retrieval semantics | yes |
| `deploy-runbook.md` | Standard VPS/AWS deploy procedure (lets Neural self-deploy / advise) | yes |
| `client-engagement.md` | Engagement workflow patterns (discovery → audit → build → train) | yes |

`pinned: true` keeps the skill curator from archiving them. These are *seed* skills; Neural's
learning loop will create more autonomously during use.

**Design note:** skills are deliberately *not* a substitute for CORTEX-PALACE. Skills =
stable procedures and reference facts that change rarely. CORTEX-PALACE = live, evolving
knowledge (current client state, recent decisions, the operator model). See 3.3.4 for the
routing rule.

### 3.3 CORTEX-PALACE bridge (`neuraledge/mcp/cortex-palace/`) — the core custom component

This is the only substantial new code in the project. Everything else is overlay/config.

#### 3.3.1 Design stance

CORTEX-PALACE already exists as a NEOS subsystem (Convex source-of-truth, FalkorDB+Graphiti
for multi-hop graph, Claude Sonnet for semantic extraction, two-phase embeddings). **We do not
rebuild it and we do not replace Hermes's native memory.** We build a *thin MCP adapter* — a
stateless bridge that exposes CORTEX-PALACE operations as MCP tools Neural can call.

Result: **two-tier memory.**
- *Tier 1 (native Hermes)* — fast working memory: current + recent sessions, SQLite FTS5
  search, Honcho user modeling. Handles "what did we say 10 minutes ago." Untouched.
- *Tier 2 (CORTEX-PALACE via MCP)* — durable institutional memory: cross-month knowledge,
  multi-hop graph queries, the deep operator/company model. Handles "what did we decide about
  the Zoo Media pricing in April."

The bridge is additive. If CORTEX-PALACE is down, Neural degrades to Tier 1 — it does not crash.

#### 3.3.2 Bridge architecture

```
   Neural (Hermes agent)
        │  MCP tool call (stdio or HTTP/SSE)
        ▼
   ┌──────────────────────────────────────────┐
   │  cortex-mcp  (FastMCP server, Python)     │
   │  ── stateless adapter ──                  │
   │  • validates tool args (pydantic)         │
   │  • maps tool → CORTEX-PALACE operation    │
   │  • handles auth, retry, timeout, circuit  │
   │  • normalizes responses → MCP content     │
   └───────────────┬──────────────────────────┘
                   │  HTTPS (Convex client API / NEOS API)
                   ▼
   ┌──────────────────────────────────────────┐
   │  CORTEX-PALACE  (existing NEOS system)    │
   │  Convex (truth) · FalkorDB+Graphiti (graph)│
   │  Wings / Halls / Rooms · L0/L1/L2 · AAAK  │
   └──────────────────────────────────────────┘
```

The bridge holds **no state** — every call is independent, auth via env-injected token. This
keeps it crash-safe and horizontally trivial.

#### 3.3.3 MCP tool contract

The bridge exposes these tools. Argument/return shapes are pydantic-validated.

```
cortex_recall(query: str, wing?: str, hall?: str, depth: int = 1, k: int = 6)
  → { results: [{ content, wing, hall, room, score, retrieved_at }],
      degraded: bool }            # degraded=true if graph/embedding tier unavailable
  Purpose: semantic + graph retrieval. depth>1 triggers FalkorDB multi-hop.

cortex_remember(content: str, wing: str, hall: str, room?: str, importance: float = 0.5)
  → { memory_id: str, stored_at: str }
  Purpose: write a durable memory. Convex is source of truth; graph/embeddings update async.

cortex_user_model(keys?: list[str])
  → { profile: { key: { value, confidence, updated_at } } }
  Purpose: fetch the operator model NEOS maintains (preferences, projects, working style).

cortex_search_entities(entity_type: str, filter?: dict, limit: int = 10)
  → { entities: [...] }
  Purpose: structured read of NEOS entities — clients, projects, Neops, engagements.

cortex_status()
  → { convex: ok|down, graph: ok|down, embeddings: ok|down, latency_ms }
  Purpose: health probe; lets Neural and `hermes doctor` see Tier-2 state.
```

**Vocabulary mapping (must stay consistent with CORTEX-PALACE):**
- *Wing* = business domain (e.g. `clients`, `product`, `operator`, `infra`).
- *Hall* = memory-type category within a wing.
- *Room* = entity/context-specific store.
- *depth* maps to L0 (direct) / L1 (1-hop) / L2 (multi-hop) retrieval tiers.

#### 3.3.4 Memory routing rule (encoded in `neos-operations.md` skill)

Neural decides which tier to use:

| Situation | Tier |
|---|---|
| "What did you just say / earlier this session" | Tier 1 native — no tool call |
| Recent (days) cross-session recall | Tier 1 native session search |
| Institutional knowledge, client/project history, decisions weeks+ old | `cortex_recall` |
| "Who/what is <NEOS entity>" | `cortex_search_entities` |
| Operator preference/working-style question | `cortex_user_model` |
| A durable fact worth keeping beyond this VPS | `cortex_remember` |

This rule lives in the skill, not in code — tunable without a rebuild.

#### 3.3.5 Resilience

- **Timeout:** every CORTEX-PALACE call capped (default 8 s).
- **Circuit breaker:** after N consecutive failures, the bridge returns `degraded: true`
  immediately for a cooldown window instead of hanging Neural.
- **Graceful degradation:** bridge errors return a structured "Tier-2 unavailable" result;
  Neural continues on Tier-1 memory and tells the operator long-term recall is offline.
- **Idempotent writes:** `cortex_remember` includes a client-generated dedupe key so retries
  don't double-write.

#### 3.3.6 Stub-first build

CORTEX-PALACE V3 may not be fully deployed. The bridge is built **stub-first**: a
`CORTEX_MODE=stub|live` env switch. In `stub` mode the tools return canned shapes so Phases
1–2 and 5 can complete and the installer can be tested end-to-end. Flip to `live` when the
real Convex/NEOS endpoint is ready — no code change, just env + the real endpoint URL.

### 3.4 Infra integration (`config` + skills, no core code)

- **n8n** — `n8n.neuraledge.in` workflows exposed to Neural either as (a) an MCP server if
  n8n's MCP endpoint is used, or (b) generic HTTP/webhook tools. Configured under
  `mcp_servers` / tool config in `config.yaml`. A skill documents which workflows exist and
  when to trigger them.
- **Matrix** — `matrix.neuraledge.in`. If Hermes ships a Matrix gateway transport, enable it
  via config. If not, **out of scope for v1** — Telegram is the v1 channel; a custom Matrix
  transport is a later sibling file under `gateway/`.
- **LLM provider** — default in `config.defaults.yaml` (OpenRouter for model flexibility, or
  Anthropic direct). `hermes model` swaps anytime.

### 3.5 Config subsystem (`neuraledge/config/`)

| File | Role |
|---|---|
| `config.defaults.yaml` | NeuralEDGE defaults: `personality: neural`, branding plugin enabled, `skills/neuraledge` path registered, `mcp_servers` listing `cortex-mcp` + n8n (CORTEX commented until keys set), provider default |
| `.env.template` | Required secrets with placeholders: `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `CORTEX_ENDPOINT`, `CORTEX_TOKEN`, `N8N_WEBHOOK_URL`, `CORTEX_MODE` |

The installer copies these into `~/.hermes` on first run **only if absent** — never clobbers
an existing operator config.

---

## 4. Deployment Architecture

### 4.1 Container topology

`docker-compose.neuraledge.yml` defines a 2-service stack on a private bridge network:

```
  network: hermes-net  (bridge, internal)

  service: hermes            service: cortex-mcp
  ─────────────────          ──────────────────
  image: neuraledge/         image: neuraledge/
    hermes-neuraledge          cortex-mcp
  cmd: gateway run           cmd: (FastMCP server)
  ports (127.0.0.1 only):    no published ports
    8642 gateway               (reached by hermes
    9119 dashboard              via hermes-net DNS
  env: HERMES_DASHBOARD=1       name "cortex-mcp")
  vol: ~/.hermes:/opt/data   env: CORTEX_MODE,
  mem 4G, shm 1g                  CORTEX_ENDPOINT,
  restart: unless-stopped         CORTEX_TOKEN
                             restart: unless-stopped
```

- `hermes` reaches the bridge as `http://cortex-mcp:<port>` — container DNS, no host exposure.
- Both `hermes` ports bound to `127.0.0.1` — not internet-reachable even if the SG allowed it.
- One volume, `~/.hermes`. Backing it up = backing up the whole agent.
- v1: build images on the VPS. v1.1: pre-build + push to `ghcr.io/neuraledge`, installer pulls.

### 4.2 The one-click installer (`neuraledge/install.sh`)

Operator's literal command: `curl -fsSL https://get.neuraledge.in/agent | bash`
(`get.neuraledge.in/agent` is a static redirect to the raw `install.sh` on the `neuraledge`
branch.)

**Execution flow (idempotent — safe to re-run):**

```
1. PRE-FLIGHT   detect OS (Ubuntu 22.04/24.04), sudo capability, RAM, existing install
2. DOCKER       install Docker Engine + Compose if absent; add user to docker group
3. SWAP         if RAM < 6 GB → create 2 GB swapfile (agent + browser tools spike)
4. FETCH        git clone -b neuraledge <origin> → /opt/neuraledge-agent
                (or git pull if already present)
5. STATE        mkdir -p ~/.hermes; copy config.defaults.yaml + .env.template if absent
6. IMAGE        docker compose build   (v1)   |   docker compose pull   (v1.1)
7. WIZARD       docker compose run --rm hermes setup
                → operator picks provider, pastes LLM key, pairs Telegram bot
                → NeuralEDGE defaults pre-seed most answers
8. SECRETS      prompt for CORTEX_ENDPOINT/CORTEX_TOKEN/N8N_WEBHOOK_URL
                → write to ~/.hermes/.env  (or leave CORTEX_MODE=stub if not ready)
9. LAUNCH       docker compose up -d
10. VERIFY      docker compose exec hermes hermes doctor
                → print success banner: Telegram pairing reminder,
                  SSH-tunnel command for dashboard, SG reminder
```

**Failure handling:** each step checks its exit status and aborts with a clear message + the
remediation command. Re-running the script resumes cleanly (steps 2–6 are no-ops if already
done).

### 4.3 Security model

| Surface | Control |
|---|---|
| Inbound network | Only SSH (22), restricted to operator IP in the AWS Security Group. Installer prints this reminder. |
| Agent ports (8642/9119) | Bound to `127.0.0.1` in compose — never `0.0.0.0`. |
| Dashboard access | SSH local-forward: `ssh -L 9119:localhost:9119 user@vps` → `http://localhost:9119`. Never `--insecure --host 0.0.0.0`. |
| Messaging | Outbound only (Telegram long-poll / websocket). No inbound port for chat. |
| Secrets | `~/.hermes/.env`, file perms `600`, never committed, never logged (Hermes redacts). |
| CORTEX-PALACE auth | Bearer token in bridge env; bridge is the only thing that holds it. |
| Container isolation | Agent-run code uses the `docker` terminal backend → sibling sandbox, not the host. |
| Volume | `~/.hermes` owned by the host operator (`HERMES_UID/GID` remap) — readable for backup, not world-writable. |

---

## 5. Key Data Flows

### 5.1 Inbound message → reply

```
Telegram msg
  → Hermes gateway (long-poll) normalizes to an Event
  → agent loop: load session, assemble context
       context = system prompt + NEURAL.md persona
                 + pinned NeuralEDGE skills (matched)
                 + Tier-1 native memory (recent sessions)
                 + Honcho user-model snippet
  → LLM call (provider) → streamed text + tool calls
  → tool calls execute:
       • native tools (shell/web/files/...) run in sandbox
       • cortex_recall / n8n tools route out via MCP
  → loop until final answer
  → reply streamed back through gateway → Telegram
  → post-turn: native memory write; skill-creation check; user-model update
```

### 5.2 Long-term recall (Tier 2)

```
Neural decides query needs institutional memory (routing rule, 3.3.4)
  → calls cortex_recall(query, wing, depth)
  → cortex-mcp validates args, calls CORTEX-PALACE over HTTPS
       depth=1 → L0/L1 (Convex + embedding search)
       depth>1 → L2 (FalkorDB/Graphiti multi-hop)
  → results normalized → returned as MCP tool result
  → if CORTEX down → circuit breaker → { degraded: true }
       → Neural answers from Tier-1 + states long-term recall is offline
```

### 5.3 Upstream sync

```
New Hermes release tagged upstream
  → git checkout main && git pull upstream main      (main mirrors upstream exactly)
  → git checkout neuraledge && git merge main
  → conflicts: expected near-zero (custom code is in neuraledge/, skills/neuraledge/,
    plugins/ne_branding/, separate compose file — all non-overlapping with upstream)
       → only real conflict risk = the ≤2 logged core patches; NEURALEDGE_PATCHES.md
         tells you exactly what they were and how to re-apply
  → rebuild image, run test checklist, tag ne-v<upstream>-<n>
```

---

## 6. Build & Release Pipeline

| Stage | Action |
|---|---|
| Dev | Work on `neuraledge` branch; `docker compose -f docker-compose.neuraledge.yml up` locally |
| Test | After each phase: `hermes doctor` green + phase acceptance check (see build spec §5) |
| Image | `Dockerfile.neuraledge` extends upstream `Dockerfile`, `COPY`s branding + skills + config; build → tag |
| Registry (v1.1) | Push `neuraledge/hermes-neuraledge` + `neuraledge/cortex-mcp` to `ghcr.io/neuraledge` |
| Release | Tag `ne-v0.14.0-1`; installer fetches this branch/tag |
| Distribution | `get.neuraledge.in/agent` → static redirect to raw `install.sh` |

---

## 7. Failure Modes & Operations

| Failure | Behaviour | Recovery |
|---|---|---|
| CORTEX-PALACE down | Bridge circuit-breaks; Neural runs Tier-1 only, says so | Auto-recovers when endpoint returns; `cortex_status` shows state |
| LLM provider error | Hermes provider fallback list kicks in | `hermes model` to switch; check provider key |
| VPS reboot | `restart: unless-stopped` brings both containers back; volume intact | None needed |
| OOM on 4 GB box | Swap (installer step 3) absorbs spikes | Resize to 8 GB if persistent |
| Telegram not replying | Usually unpaired bot or bad token | Re-run wizard; check `~/.hermes` credentials writable |
| Upstream merge conflict | Only in a logged core patch | `NEURALEDGE_PATCHES.md` has the exact re-apply |
| Bad config after edit | `hermes doctor` reports it | Restore `~/.hermes/config.yaml` from backup |

**Backup:** `tar czf hermes-backup-$(date +%F).tar.gz -C ~ .hermes` — cron it. Restore =
extract + `docker compose up -d`.

**Observability:** `docker compose logs -f hermes` (structured JSON logs, secrets redacted);
`hermes doctor` for health; `cortex_status` for Tier-2.

---

## 8. Scope Boundaries

**In scope (v1):** branded Neural agent, full Hermes feature set, NeuralEDGE skills,
CORTEX-PALACE MCP bridge (stub + live), n8n integration, Telegram channel, one-click
installer, 2-service Docker stack, upstream-syncable fork.

**Deferred:** Matrix transport (custom gateway file — v1.x), pre-built registry images
(v1.1), CORTEX-PALACE *replacing* native memory (only if a clean backend interface is found
on code review), multi-operator support, dashboard feature additions beyond retheme.

**Never:** editing Hermes core beyond the ≤2 logged minimal patches; exposing agent ports to
the internet; rebuilding CORTEX-PALACE inside this repo.

---

## 9. Open Decisions (resolve before/early in build)

1. **Image strategy for v1** — build-on-VPS (simple, ~slower install) vs pre-built registry
   (faster, needs `ghcr.io/neuraledge` set up). *Recommendation: build-on-VPS for v1, registry at v1.1.*
2. **CORTEX-PALACE readiness** — is the Convex/NEOS endpoint live enough for `cortex_recall`?
   If not, ship `CORTEX_MODE=stub` and wire live later. *Build is stub-first regardless.*
3. **n8n exposure** — native n8n MCP endpoint vs generic webhook tools. Depends on the n8n
   version at `n8n.neuraledge.in`. Confirm before Phase 4.
4. **LLM provider default** — OpenRouter (flexibility) vs Anthropic direct (quality/latency).
   Set in `config.defaults.yaml`.

---

## 10. Traceability to the Build Spec

| Build-spec phase | This design's sections |
|---|---|
| Phase 0 — Fork & baseline | §2 (fork seam), §4.1 |
| Phase 1 — Branding | §3.1 |
| Phase 2 — Skills | §3.2 |
| Phase 3 — CORTEX-PALACE MCP | §3.3 (all) |
| Phase 4 — Infra wiring | §3.4, §3.5 |
| Phase 5 — One-click installer | §4.2, §4.3 |
| Phase 6 — Polish & docs | §6 |

Build with `NEURALEDGE_BUILD.md` open for the phase order and acceptance checks; consult this
document for contracts, data shapes, and the reasoning behind each boundary.
