# cortex-mcp — CORTEX-PALACE MCP bridge

A stateless [MCP](https://modelcontextprotocol.io) server that exposes NEOS
CORTEX-PALACE as 5 tools Neural can call. Lives in the NeuralEDGE zone of the
Hermes fork.

See `NEURALEDGE_DESIGN.md` §3.3 for the full design.

## Run modes

| `CORTEX_MODE` | Behaviour |
|---|---|
| `stub` (default) | Returns canned NeuralEDGE-shaped data. Works out of the box. |
| `live` | Calls the real CORTEX-PALACE endpoint via HTTPS. Requires `CORTEX_ENDPOINT` + `CORTEX_TOKEN`. |

Flipping modes is an env change — no rebuild needed.

## Env vars

| Name | Default | Purpose |
|---|---|---|
| `CORTEX_MODE` | `stub` | `stub` or `live` |
| `CORTEX_ENDPOINT` | — | Base URL for live mode (e.g. `https://cortex.neos.internal`) |
| `CORTEX_TOKEN` | — | Bearer token for live mode |
| `CORTEX_TIMEOUT_S` | `8.0` | Per-call timeout |
| `CORTEX_BREAKER_THRESHOLD` | `5` | Failures before circuit opens |
| `CORTEX_BREAKER_COOLDOWN_S` | `30` | Open-circuit cooldown |
| `CORTEX_MCP_TRANSPORT` | `stdio` (CLI) / `sse` (container) | MCP transport |
| `HOST` | `0.0.0.0` | SSE bind host |
| `PORT` | `8765` | SSE bind port |
| `CORTEX_LOG_LEVEL` | `INFO` | Python logging level |

## Tools

| Tool | Purpose |
|---|---|
| `cortex_recall(query, wing?, hall?, depth=1, k=6)` | Semantic + graph retrieval |
| `cortex_remember(content, wing, hall, room?, importance=0.5, dedupe_key?)` | Write a durable memory |
| `cortex_user_model(keys?)` | Operator's persistent model |
| `cortex_search_entities(entity_type, filter?, limit=10)` | Structured NEOS entity lookup |
| `cortex_status()` | Health probe (convex/graph/embeddings/breaker) |

Vocabulary: **Wing** (domain) → **Hall** (category) → **Room** (entity). Depth
maps to L0/L1/L2 retrieval tiers. See `skills/neuraledge/neos-operations.md`
for the routing rule Neural follows.

## Local development

```bash
# Install
cd neuraledge/mcp/cortex-palace
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run stdio (for `mcp dev` or direct Hermes wiring)
python -m cortex_mcp.server

# Run SSE on localhost:8765
CORTEX_MCP_TRANSPORT=sse python -m cortex_mcp.server

# Healthcheck (exits 0 if reachable)
python -m cortex_mcp.healthcheck

# Lint + test
ruff check .
pytest
```

## Docker

```bash
docker build -t neuraledge/cortex-mcp .
docker run --rm -p 8765:8765 -e CORTEX_MODE=stub neuraledge/cortex-mcp
```

In production it's launched by `docker-compose.neuraledge.yml` as the
`cortex-mcp` service on the `hermes-net` bridge; the `hermes` service reaches
it via `http://cortex-mcp:8765/sse`.

## Resilience contract

- **Timeout:** every call bounded by `CORTEX_TIMEOUT_S`.
- **Circuit breaker:** opens after `CORTEX_BREAKER_THRESHOLD` consecutive
  failures and stays open for `CORTEX_BREAKER_COOLDOWN_S` seconds. While open,
  reads return `degraded: true` immediately and writes return a
  `pending-breaker-open` id.
- **Idempotent writes:** pass `dedupe_key` to `cortex_remember` to make retries safe.
- **Stateless:** crash-safe and trivially horizontal.

## Live-mode HTTP contract (provisional)

The live client expects this REST shape on `CORTEX_ENDPOINT`. Adjust in
`client.py` when NEOS publishes its final API; the MCP tool shapes (this
repo's `models.py`) stay stable.

```
POST /recall             body: RecallArgs    →  CortexRecallResult
POST /remember           body: RememberArgs  →  CortexRememberResult
GET  /user-model         q: keys=…           →  CortexUserModel
POST /entities/search    body: SearchArgs    →  CortexEntitiesResult
GET  /status             —                   →  CortexStatus
```
