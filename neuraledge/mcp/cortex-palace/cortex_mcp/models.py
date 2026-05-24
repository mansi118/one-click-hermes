"""Pydantic models for cortex-mcp tool arguments and responses.

Shapes are authoritative — they're what Neural sees in tool results. Keep them
stable; additive changes only. Removing or renaming a field is a breaking
change to Neural's tool surface.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt, confloat

# --- Vocabulary ---------------------------------------------------------------

Wing = str   # business domain — e.g. "clients", "product", "operator", "infra"
Hall = str   # memory-type category within a wing
Room = str   # entity/context-specific store


# --- cortex_recall ------------------------------------------------------------


class RecallArgs(BaseModel):
    """Args for cortex_recall."""

    query: str = Field(min_length=1, max_length=2000)
    wing: Wing | None = None
    hall: Hall | None = None
    depth: NonNegativeInt = 1
    k: PositiveInt = 6


class RecallItem(BaseModel):
    """One item returned by cortex_recall."""

    content: str
    wing: Wing
    hall: Hall
    room: Room | None = None
    score: confloat(ge=0.0, le=1.0) = 0.0  # type: ignore[valid-type]
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Literal["convex", "graph", "embedding", "stub"] = "convex"
    memory_id: str | None = None


class CortexRecallResult(BaseModel):
    """Return shape for cortex_recall."""

    results: list[RecallItem]
    degraded: bool = False
    depth_used: NonNegativeInt = 1
    note: str | None = None  # optional explanation when degraded


# --- cortex_remember ----------------------------------------------------------


class RememberArgs(BaseModel):
    """Args for cortex_remember."""

    content: str = Field(min_length=1, max_length=20_000)
    wing: Wing = Field(min_length=1)
    hall: Hall = Field(min_length=1)
    room: Room | None = None
    importance: confloat(ge=0.0, le=1.0) = 0.5  # type: ignore[valid-type]
    dedupe_key: str | None = None


class CortexRememberResult(BaseModel):
    """Return shape for cortex_remember."""

    memory_id: str
    stored_at: datetime
    deduplicated: bool = False
    degraded: bool = False


# --- cortex_user_model --------------------------------------------------------


class UserModelArgs(BaseModel):
    """Args for cortex_user_model. `keys` filters; empty → full profile."""

    keys: list[str] | None = None


class UserModelEntry(BaseModel):
    """One entry of the operator's persistent model."""

    value: Any
    confidence: confloat(ge=0.0, le=1.0)  # type: ignore[valid-type]
    updated_at: datetime
    source: str | None = None


class CortexUserModel(BaseModel):
    """Return shape for cortex_user_model."""

    profile: dict[str, UserModelEntry]
    degraded: bool = False


# --- cortex_search_entities ---------------------------------------------------


EntityType = Literal["client", "project", "neop", "engagement", "team_member"]


class SearchEntitiesArgs(BaseModel):
    """Args for cortex_search_entities."""

    entity_type: EntityType
    filter: dict[str, Any] | None = None
    limit: PositiveInt = 10


class CortexEntity(BaseModel):
    """One entity row from NEOS."""

    id: str
    entity_type: EntityType
    name: str
    slug: str | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class CortexEntitiesResult(BaseModel):
    """Return shape for cortex_search_entities."""

    entities: list[CortexEntity]
    degraded: bool = False
    total: NonNegativeInt | None = None


# --- cortex_status ------------------------------------------------------------


class TierStatus(BaseModel):
    """Status of a CORTEX-PALACE sub-tier."""

    state: Literal["ok", "degraded", "down"] = "ok"
    latency_ms: NonNegativeInt | None = None
    note: str | None = None


class CortexStatus(BaseModel):
    """Return shape for cortex_status."""

    mode: Literal["stub", "live"]
    convex: TierStatus
    graph: TierStatus
    embeddings: TierStatus
    breaker_open: bool = False
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
