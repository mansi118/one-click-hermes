"""Canned stub responses for cortex-mcp.

Shapes are realistic NeuralEDGE data so Neural's prompts and tool-trace logs
look identical between stub and live mode. Update when the NEOS schema
evolves to keep stub plausible.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    CortexEntitiesResult,
    CortexEntity,
    CortexRecallResult,
    CortexRememberResult,
    CortexStatus,
    CortexUserModel,
    RecallItem,
    TierStatus,
    UserModelEntry,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- cortex_recall stub ------------------------------------------------------


def stub_recall(query: str, wing: str | None, hall: str | None, depth: int, k: int) -> CortexRecallResult:
    """Return realistic-shaped canned recall hits."""
    items = [
        RecallItem(
            content=(
                "Phase pricing for AI Audit is per phase, not bundled. Each gate is a "
                "real off-ramp. (Captured: 2026-01-14)"
            ),
            wing=wing or "operator",
            hall=hall or "principles",
            room="pricing",
            score=0.91,
            source="stub",
            memory_id="stub-mem-001",
        ),
        RecallItem(
            content=(
                "Zoo Media engagement: Audit closed at ₹6.5L for the L1 support workflow "
                "scope; Build phase signed 2026-02-03."
            ),
            wing="clients",
            hall="decisions",
            room="zoo-media",
            score=0.87,
            source="stub",
            memory_id="stub-mem-014",
        ),
        RecallItem(
            content=(
                "Operator prefers Hinglish for casual context, English for ops/runbook "
                "outputs. Confirmed multiple sessions."
            ),
            wing="operator",
            hall="preferences",
            room="voice",
            score=0.82,
            source="stub",
            memory_id="stub-mem-022",
        ),
    ][:k]
    return CortexRecallResult(
        results=items,
        degraded=False,
        depth_used=depth,
        note="stub mode — switch CORTEX_MODE=live for real recall",
    )


# --- cortex_remember stub ----------------------------------------------------


def stub_remember(content: str, wing: str, hall: str, room: str | None, dedupe_key: str | None) -> CortexRememberResult:
    """Pretend to store; return a stable id so retries look idempotent."""
    suffix = dedupe_key or f"{wing}-{hall}-{room or 'na'}-{hash(content) & 0xFFFFFF:06x}"
    return CortexRememberResult(
        memory_id=f"stub-mem-{suffix}",
        stored_at=_now(),
        deduplicated=dedupe_key is not None,
        degraded=False,
    )


# --- cortex_user_model stub --------------------------------------------------


def stub_user_model(keys: list[str] | None) -> CortexUserModel:
    """Operator model fragment — close enough to drive plausible prompt routing."""
    full = {
        "address_as": UserModelEntry(
            value="Yatharth Sir (formal) / ML (casual)",
            confidence=0.95,
            updated_at=_now(),
            source="stub",
        ),
        "language_pref": UserModelEntry(
            value="Hinglish in casual, English in operational",
            confidence=0.88,
            updated_at=_now(),
            source="stub",
        ),
        "active_projects": UserModelEntry(
            value=["NeuralEDGE Agent (Neural)", "NEOS v3", "Zoo Media Build"],
            confidence=0.9,
            updated_at=_now(),
            source="stub",
        ),
        "working_style": UserModelEntry(
            value="Direct, low-tolerance for filler; prefers short responses",
            confidence=0.93,
            updated_at=_now(),
            source="stub",
        ),
    }
    if keys:
        return CortexUserModel(profile={k: v for k, v in full.items() if k in keys})
    return CortexUserModel(profile=full)


# --- cortex_search_entities stub --------------------------------------------


_STUB_ENTITIES: dict[str, list[CortexEntity]] = {
    "client": [
        CortexEntity(
            id="ent-c-001",
            entity_type="client",
            name="Zoo Media",
            slug="zoo-media",
            attrs={"sector": "media", "icp_fit": True, "stage": "build"},
            updated_at=_now(),
        ),
        CortexEntity(
            id="ent-c-002",
            entity_type="client",
            name="Acme Logistics",
            slug="acme-logistics",
            attrs={"sector": "logistics", "icp_fit": True, "stage": "audit"},
            updated_at=_now(),
        ),
    ],
    "project": [
        CortexEntity(
            id="ent-p-001",
            entity_type="project",
            name="NeuralEDGE Agent",
            slug="neural",
            attrs={"internal": True, "version": "0.14.0-ne1"},
            updated_at=_now(),
        ),
    ],
    "neop": [
        CortexEntity(
            id="ent-n-001",
            entity_type="neop",
            name="L1 Support Neop",
            slug="l1-support",
            attrs={"deployed_at": "zoo-media", "status": "shadow"},
            updated_at=_now(),
        ),
    ],
    "engagement": [],
    "team_member": [],
}


def stub_search_entities(entity_type: str, filter: dict | None, limit: int) -> CortexEntitiesResult:
    pool = _STUB_ENTITIES.get(entity_type, [])
    if filter:
        def _match(e: CortexEntity) -> bool:
            for k, v in filter.items():
                if getattr(e, k, None) != v and e.attrs.get(k) != v and e.slug != v:
                    return False
            return True

        pool = [e for e in pool if _match(e)]
    return CortexEntitiesResult(entities=pool[:limit], total=len(pool), degraded=False)


# --- cortex_status stub ------------------------------------------------------


def stub_status() -> CortexStatus:
    return CortexStatus(
        mode="stub",
        convex=TierStatus(state="ok", latency_ms=2, note="stub"),
        graph=TierStatus(state="ok", latency_ms=3, note="stub"),
        embeddings=TierStatus(state="ok", latency_ms=4, note="stub"),
        breaker_open=False,
    )
