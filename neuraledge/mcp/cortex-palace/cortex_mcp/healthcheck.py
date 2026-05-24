"""Standalone healthcheck — exits 0 if cortex-mcp can reach its backend.

Used by the Docker HEALTHCHECK directive and by `hermes doctor`. Does not
require the MCP transport to be up — it instantiates a CortexClient and calls
status() directly. Exit code 0 = ok, 1 = down.
"""

from __future__ import annotations

import asyncio
import json
import sys

from .client import CortexClient


async def _run() -> int:
    client = CortexClient()
    try:
        status = await client.status()
        print(json.dumps(status.model_dump(mode="json"), default=str))
        # In stub mode anything other than explicit "down" is healthy.
        if client.mode == "stub":
            return 0
        # Live mode: all three tiers must be at least degraded (not down) to pass.
        for tier in (status.convex, status.graph, status.embeddings):
            if tier.state == "down":
                return 1
        return 0
    finally:
        await client.aclose()


def main() -> None:
    code = asyncio.run(_run())
    sys.exit(code)


if __name__ == "__main__":
    main()
