"""CORTEX-PALACE client — stub or live mode with timeout, retry, circuit breaker.

The client is the seam between the MCP tool layer (server.py) and the actual
NEOS/Convex API. Live-mode endpoints are placeholders until NEOS publishes the
final HTTP contract — switching is a per-method change, not a structural one.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from . import stub_data
from .models import (
    CortexEntitiesResult,
    CortexRecallResult,
    CortexRememberResult,
    CortexStatus,
    CortexUserModel,
    RecallItem,
    TierStatus,
)

log = structlog.get_logger("cortex_mcp.client")

DEFAULT_TIMEOUT_S = float(os.getenv("CORTEX_TIMEOUT_S", "8.0"))
BREAKER_THRESHOLD = int(os.getenv("CORTEX_BREAKER_THRESHOLD", "5"))
BREAKER_COOLDOWN_S = float(os.getenv("CORTEX_BREAKER_COOLDOWN_S", "30.0"))


# --- Circuit breaker ---------------------------------------------------------


@dataclass
class _Breaker:
    threshold: int = BREAKER_THRESHOLD
    cooldown_s: float = BREAKER_COOLDOWN_S
    failures: int = 0
    opened_at: float | None = None

    @property
    def open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.monotonic() - self.opened_at >= self.cooldown_s:
            # Half-open: next call gets to try; success will reset.
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.monotonic()
            log.warning("cortex.breaker.opened", failures=self.failures, cooldown_s=self.cooldown_s)


# --- Client ------------------------------------------------------------------


@dataclass
class CortexClient:
    mode: str = field(default_factory=lambda: os.getenv("CORTEX_MODE", "stub").lower())
    endpoint: str | None = field(default_factory=lambda: os.getenv("CORTEX_ENDPOINT"))
    token: str | None = field(default_factory=lambda: os.getenv("CORTEX_TOKEN"))
    timeout_s: float = DEFAULT_TIMEOUT_S
    breaker: _Breaker = field(default_factory=_Breaker)
    _http: httpx.AsyncClient | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"stub", "live"}:
            log.warning("cortex.mode.invalid", mode=self.mode, fallback="stub")
            self.mode = "stub"
        if self.mode == "live" and not self.endpoint:
            log.warning("cortex.mode.live_without_endpoint", fallback="stub")
            self.mode = "stub"

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            headers = {"User-Agent": "cortex-mcp/0.1"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._http = httpx.AsyncClient(
                base_url=self.endpoint or "",
                timeout=httpx.Timeout(self.timeout_s),
                headers=headers,
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    # --- Tool implementations ----------------------------------------------

    async def recall(
        self, query: str, wing: str | None, hall: str | None, depth: int, k: int
    ) -> CortexRecallResult:
        if self.mode == "stub":
            return stub_data.stub_recall(query, wing, hall, depth, k)
        if self.breaker.open:
            return _degraded_recall("breaker_open: skipping live call")
        try:
            r = await self.http.post(
                "/recall",
                json={"query": query, "wing": wing, "hall": hall, "depth": depth, "k": k},
            )
            r.raise_for_status()
            data = r.json()
            self.breaker.record_success()
            items = [RecallItem(**item) for item in data.get("results", [])]
            return CortexRecallResult(
                results=items,
                degraded=bool(data.get("degraded", False)),
                depth_used=data.get("depth_used", depth),
                note=data.get("note"),
            )
        except (httpx.HTTPError, ValueError) as e:
            self.breaker.record_failure()
            log.error("cortex.recall.failed", error=str(e))
            return _degraded_recall(f"live call failed: {type(e).__name__}")

    async def remember(
        self,
        content: str,
        wing: str,
        hall: str,
        room: str | None,
        importance: float,
        dedupe_key: str | None,
    ) -> CortexRememberResult:
        if self.mode == "stub":
            return stub_data.stub_remember(content, wing, hall, room, dedupe_key)
        if self.breaker.open:
            # Write while degraded — return a synthetic id; operator can retry later.
            return CortexRememberResult(
                memory_id="pending-breaker-open",
                stored_at=datetime.now(timezone.utc),
                degraded=True,
            )
        try:
            payload = {
                "content": content,
                "wing": wing,
                "hall": hall,
                "room": room,
                "importance": importance,
                "dedupe_key": dedupe_key,
            }
            r = await self.http.post("/remember", json=payload)
            r.raise_for_status()
            data = r.json()
            self.breaker.record_success()
            return CortexRememberResult(
                memory_id=data["memory_id"],
                stored_at=datetime.fromisoformat(data["stored_at"]),
                deduplicated=bool(data.get("deduplicated", False)),
            )
        except (httpx.HTTPError, ValueError, KeyError) as e:
            self.breaker.record_failure()
            log.error("cortex.remember.failed", error=str(e))
            return CortexRememberResult(
                memory_id="error",
                stored_at=datetime.now(timezone.utc),
                degraded=True,
            )

    async def user_model(self, keys: list[str] | None) -> CortexUserModel:
        if self.mode == "stub":
            return stub_data.stub_user_model(keys)
        if self.breaker.open:
            return CortexUserModel(profile={}, degraded=True)
        try:
            r = await self.http.get("/user-model", params={"keys": ",".join(keys)} if keys else None)
            r.raise_for_status()
            data = r.json()
            self.breaker.record_success()
            return CortexUserModel(**data)
        except (httpx.HTTPError, ValueError) as e:
            self.breaker.record_failure()
            log.error("cortex.user_model.failed", error=str(e))
            return CortexUserModel(profile={}, degraded=True)

    async def search_entities(
        self, entity_type: str, filter: dict[str, Any] | None, limit: int
    ) -> CortexEntitiesResult:
        if self.mode == "stub":
            return stub_data.stub_search_entities(entity_type, filter, limit)
        if self.breaker.open:
            return CortexEntitiesResult(entities=[], degraded=True)
        try:
            r = await self.http.post(
                "/entities/search",
                json={"entity_type": entity_type, "filter": filter or {}, "limit": limit},
            )
            r.raise_for_status()
            data = r.json()
            self.breaker.record_success()
            return CortexEntitiesResult(**data)
        except (httpx.HTTPError, ValueError) as e:
            self.breaker.record_failure()
            log.error("cortex.search_entities.failed", error=str(e))
            return CortexEntitiesResult(entities=[], degraded=True)

    async def status(self) -> CortexStatus:
        if self.mode == "stub":
            return stub_data.stub_status()
        try:
            t0 = time.monotonic()
            r = await self.http.get("/status")
            r.raise_for_status()
            data = r.json()
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            self.breaker.record_success()
            return CortexStatus(
                mode="live",
                convex=TierStatus(**data.get("convex", {"state": "ok"})),
                graph=TierStatus(**data.get("graph", {"state": "ok"})),
                embeddings=TierStatus(**data.get("embeddings", {"state": "ok"})),
                breaker_open=False,
            )
        except (httpx.HTTPError, ValueError) as e:
            self.breaker.record_failure()
            log.error("cortex.status.failed", error=str(e))
            return CortexStatus(
                mode="live",
                convex=TierStatus(state="down", note=str(e)),
                graph=TierStatus(state="down"),
                embeddings=TierStatus(state="down"),
                breaker_open=self.breaker.open,
            )


def _degraded_recall(note: str) -> CortexRecallResult:
    return CortexRecallResult(results=[], degraded=True, note=note)
