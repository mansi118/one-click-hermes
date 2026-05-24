---
name: neos-operations
description: How and when to query CORTEX-PALACE (NEOS long-term memory). Wings/Halls/Rooms vocabulary, L0/L1/L2 depth semantics, the two-tier memory routing rule, and the five cortex_* MCP tools. Load whenever the operator asks something that might require institutional memory or when you're deciding which memory tier to use.
pinned: true
priority: 95
tags: [neuraledge, neos, cortex-palace, memory, mcp]
version: 1.0.0
---

# Two-tier memory — the routing rule (read first)

You have two memory systems. Use the right one.

| Situation | Use |
|---|---|
| "What did you just say / earlier this message thread" | **Tier 1** native — no tool call |
| Recall within the last day or two, cross-session but recent | **Tier 1** native session search |
| Institutional knowledge — client/project history, decisions weeks+ old | **Tier 2** `cortex_recall` |
| "Who/what is <NEOS entity>" — a client, project, Neop, engagement | **Tier 2** `cortex_search_entities` |
| Operator preference / working style question | **Tier 2** `cortex_user_model` |
| A durable fact worth keeping beyond this VPS | **Tier 2** `cortex_remember` |
| Health check — "is long-term memory up?" | **Tier 2** `cortex_status` |

Default to Tier 1. Reach for Tier 2 only when the question genuinely needs institutional
memory. Tool calls cost latency and the operator notices.

# Vocabulary (must stay consistent with CORTEX-PALACE)

- **Wing** — a business *domain*. Examples: `clients`, `product`, `operator`, `infra`,
  `engagements`, `team`.
- **Hall** — a *category of memory* within a wing. Example: under `clients` → `profiles`,
  `decisions`, `incidents`, `meetings`.
- **Room** — an *entity-specific store* under a hall. Example: under `clients/profiles`
  → `zoo-media`, `acme-corp`. One room per entity.

When you don't know the right wing/hall/room, omit it — `cortex_recall` will search
broadly. Specify them when you do know; it sharpens results dramatically.

# Depth → tier mapping

- `depth = 0` (L0) — direct lookup, Convex only. Fastest. Good for "give me the latest
  decision on X".
- `depth = 1` (L1, default) — Convex + embedding search. Semantic recall. Use for "what
  did we say about Y."
- `depth ≥ 2` (L2) — engages FalkorDB/Graphiti multi-hop. Use sparingly — for "what
  connects A to B" or "which clients have we built X for and what came next."

Higher depth is slower and more expensive. Don't ask for L2 unless the question is
genuinely relational.

# The 5 MCP tools

### `cortex_recall(query, wing?, hall?, depth=1, k=6)`
Semantic + graph retrieval. Returns `{results: [...], degraded: bool}`. If
`degraded: true`, the embedding or graph tier is down — answer from what came back
and *tell the operator* the recall was limited.

### `cortex_remember(content, wing, hall, room?, importance=0.5)`
Writes a durable memory. Use when the operator gives you something institutional:
a pricing decision, a vendor outcome, a "from now on" preference at company scope,
a postmortem fact. Returns `{memory_id, stored_at}`. Idempotent on repeat content.

### `cortex_user_model(keys?)`
Returns the operator's persistent model — preferences, current projects, working
style. Use when you're about to make a stylistic or scheduling decision and want to
check the operator's known preference.

### `cortex_search_entities(entity_type, filter?, limit=10)`
Structured read. `entity_type` ∈ {`client`, `project`, `neop`, `engagement`, `team_member`}.
Use this — not `cortex_recall` — when you want a clean list of entities, e.g. "list
all active client engagements".

### `cortex_status()`
Returns `{convex, graph, embeddings, latency_ms}`. Run this before a heavy multi-hop
query if you're unsure, and any time the operator asks "is long-term memory up?".

# Stub vs live mode

`CORTEX_MODE=stub` returns canned, NeuralEDGE-shaped data so the agent works even when
the real CORTEX endpoint isn't configured. If you notice every recall returning the same
3 fake results — you're in stub mode. Say so when relevant.

`CORTEX_MODE=live` hits the real Convex/NEOS endpoint. Configure `CORTEX_ENDPOINT` and
`CORTEX_TOKEN` in `~/.hermes/.env` to switch.

# When Tier 2 is degraded

Do not stall. Do not invent. Answer from Tier 1 and explicitly say:
*"Long-term memory is currently degraded — answering from working context. I'll retry
the full recall when CORTEX is back."* Then continue.

# When to write (`cortex_remember`)

Write durable memories when you hear:
- A decision the operator wants to outlast this session ("from now on, always X").
- A factual outcome that future-Neural will need ("we ended up pricing the Zoo Media
  audit at ₹X for Y scope").
- A new entity worth tracking (a new client name, a new vendor, a new internal tool).

Don't write:
- Chitchat, transient context, debug output, partial thoughts.
- Anything the operator hasn't validated (uncertain inferences).
- Duplicates — `cortex_remember` is idempotent but the noise still costs tokens later.

Pick the wing/hall by the rule of thumb: "if I needed this back in 3 months, where would
I look?" That's the right path.
