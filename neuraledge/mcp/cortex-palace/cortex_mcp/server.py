"""FastMCP server exposing the 5 cortex_* tools to Hermes/Neural.

Run:
    python -m cortex_mcp.server                # stdio transport (default for MCP)
    CORTEX_MCP_TRANSPORT=sse python -m cortex_mcp.server   # SSE on $PORT

Env vars (see README):
    CORTEX_MODE=stub|live
    CORTEX_ENDPOINT=...
    CORTEX_TOKEN=...
    CORTEX_TIMEOUT_S=8
    CORTEX_BREAKER_THRESHOLD=5
    CORTEX_BREAKER_COOLDOWN_S=30
    CORTEX_MCP_TRANSPORT=stdio|sse
    PORT=8765  (only for sse transport)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog
from mcp.server.fastmcp import FastMCP

from .client import CortexClient
from .models import (
    CortexEntitiesResult,
    CortexRecallResult,
    CortexRememberResult,
    CortexStatus,
    CortexUserModel,
    EntityType,
)


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("CORTEX_LOG_LEVEL", "INFO").upper(),
        format="%(message)s",
        stream=sys.stderr,  # MCP stdio uses stdout for protocol; logs go to stderr.
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )


_configure_logging()
log = structlog.get_logger("cortex_mcp.server")

mcp = FastMCP(
    name="cortex-palace",
    instructions=(
        "NeuralEDGE long-term memory bridge. Use cortex_recall for semantic/graph "
        "retrieval, cortex_remember to write durable memories, cortex_user_model for "
        "the operator profile, cortex_search_entities for structured NEOS entities, "
        "and cortex_status for health. See the neos-operations skill for the routing rule."
    ),
)

_client = CortexClient()
log.info("cortex_mcp.boot", mode=_client.mode, endpoint=_client.endpoint or "n/a")


# --- Tools ------------------------------------------------------------------


@mcp.tool(name="cortex_recall")
async def cortex_recall(
    query: str,
    wing: str | None = None,
    hall: str | None = None,
    depth: int = 1,
    k: int = 6,
) -> dict[str, Any]:
    """Semantic + graph recall from CORTEX-PALACE.

    Args:
        query: Natural-language query.
        wing: Optional business domain ("clients", "product", "operator", "infra").
        hall: Optional category within the wing.
        depth: 0 = direct (L0), 1 = embedding (L1, default), >=2 = multi-hop (L2).
        k: Max results.
    """
    result: CortexRecallResult = await _client.recall(query, wing, hall, depth, k)
    return result.model_dump(mode="json")


@mcp.tool(name="cortex_remember")
async def cortex_remember(
    content: str,
    wing: str,
    hall: str,
    room: str | None = None,
    importance: float = 0.5,
    dedupe_key: str | None = None,
) -> dict[str, Any]:
    """Write a durable memory into CORTEX-PALACE.

    Args:
        content: The memory text.
        wing: Business domain (required).
        hall: Memory category within the wing (required).
        room: Optional entity/context-specific store slug.
        importance: 0.0 – 1.0; affects retention and recall priority.
        dedupe_key: Optional client-side key to make retries idempotent.
    """
    result: CortexRememberResult = await _client.remember(
        content, wing, hall, room, importance, dedupe_key
    )
    return result.model_dump(mode="json")


@mcp.tool(name="cortex_user_model")
async def cortex_user_model(keys: list[str] | None = None) -> dict[str, Any]:
    """Fetch the operator's persistent model (preferences, projects, working style).

    Args:
        keys: Optional list of keys to filter to; empty/None returns the full profile.
    """
    result: CortexUserModel = await _client.user_model(keys)
    return result.model_dump(mode="json")


@mcp.tool(name="cortex_search_entities")
async def cortex_search_entities(
    entity_type: EntityType,
    filter: dict[str, Any] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Structured read of NEOS entities.

    Args:
        entity_type: One of client | project | neop | engagement | team_member.
        filter: Optional filter dict (e.g. {"slug": "zoo-media"}).
        limit: Max results (default 10).
    """
    result: CortexEntitiesResult = await _client.search_entities(entity_type, filter, limit)
    return result.model_dump(mode="json")


@mcp.tool(name="cortex_status")
async def cortex_status() -> dict[str, Any]:
    """Health probe for CORTEX-PALACE — convex/graph/embeddings/breaker state."""
    result: CortexStatus = await _client.status()
    return result.model_dump(mode="json")


# --- Entrypoint -------------------------------------------------------------


def main() -> None:
    transport = os.getenv("CORTEX_MCP_TRANSPORT", "stdio").lower()
    log.info("cortex_mcp.starting", transport=transport)
    if transport == "sse":
        # SSE binds to $HOST:$PORT and is reachable over hermes-net Docker bridge.
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8765"))
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
