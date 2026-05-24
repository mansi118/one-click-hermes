"""Stub-mode smoke tests. Validates the tool surface returns documented shapes
even when CORTEX-PALACE is unavailable — guarantees Phase 1–2 of the build
can complete without a live NEOS endpoint.
"""

from __future__ import annotations

import os

import pytest

from cortex_mcp.client import CortexClient
from cortex_mcp.models import (
    CortexEntitiesResult,
    CortexRecallResult,
    CortexRememberResult,
    CortexStatus,
    CortexUserModel,
)


@pytest.fixture(autouse=True)
def _force_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_MODE", "stub")
    # Defensive: drop endpoint so a stray env var can't force live mode.
    monkeypatch.delenv("CORTEX_ENDPOINT", raising=False)


@pytest.fixture
async def client() -> CortexClient:  # type: ignore[misc]
    c = CortexClient()
    try:
        yield c
    finally:
        await c.aclose()


async def test_recall_returns_documented_shape(client: CortexClient) -> None:
    r = await client.recall("anything", wing=None, hall=None, depth=1, k=3)
    assert isinstance(r, CortexRecallResult)
    assert 1 <= len(r.results) <= 3
    for item in r.results:
        assert item.content
        assert item.wing
        assert item.hall
        assert 0.0 <= item.score <= 1.0


async def test_remember_returns_id(client: CortexClient) -> None:
    r = await client.remember(
        content="test memory", wing="operator", hall="preferences", room=None,
        importance=0.7, dedupe_key="t1",
    )
    assert isinstance(r, CortexRememberResult)
    assert r.memory_id.startswith("stub-mem-")
    assert r.deduplicated is True


async def test_user_model_full_and_filtered(client: CortexClient) -> None:
    full = await client.user_model(None)
    assert isinstance(full, CortexUserModel)
    assert "address_as" in full.profile

    filtered = await client.user_model(["language_pref"])
    assert set(filtered.profile.keys()) == {"language_pref"}


async def test_search_entities_filter(client: CortexClient) -> None:
    all_clients = await client.search_entities("client", None, 10)
    assert isinstance(all_clients, CortexEntitiesResult)
    assert any(e.slug == "zoo-media" for e in all_clients.entities)

    one = await client.search_entities("client", {"slug": "zoo-media"}, 10)
    assert len(one.entities) == 1
    assert one.entities[0].slug == "zoo-media"


async def test_status_ok(client: CortexClient) -> None:
    s = await client.status()
    assert isinstance(s, CortexStatus)
    assert s.mode == "stub"
    assert s.convex.state == "ok"
    assert s.graph.state == "ok"
    assert s.embeddings.state == "ok"
    assert s.breaker_open is False


def test_invalid_mode_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_MODE", "garbage")
    c = CortexClient()
    assert c.mode == "stub"


def test_live_without_endpoint_falls_back_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_MODE", "live")
    monkeypatch.delenv("CORTEX_ENDPOINT", raising=False)
    c = CortexClient()
    assert c.mode == "stub"
