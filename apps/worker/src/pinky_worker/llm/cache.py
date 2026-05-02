"""Investigation artifact caching — avoids duplicate LLM work.

Cache key: (correlation_key, evidence_hash).
If a valid cached artifact exists with matching evidence hash and is
less than max_age old, return it instead of re-running LLM reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class CachedArtifact:
    artifact_id: str
    correlation_key: str
    evidence_hash: str
    summary: str
    recommended_action: str
    confidence: float
    tool_calls: list[str]
    created_at: datetime


class ArtifactCache:
    """In-memory cache for testing. Production uses Postgres."""

    def __init__(self, max_age: timedelta = timedelta(hours=1)) -> None:
        self._store: dict[tuple[str, str], CachedArtifact] = {}
        self.max_age = max_age
        self.hits = 0
        self.misses = 0

    def get(self, correlation_key: str, evidence_hash: str) -> CachedArtifact | None:
        key = (correlation_key, evidence_hash)
        artifact = self._store.get(key)
        if artifact is None:
            self.misses += 1
            return None

        age = datetime.now(timezone.utc) - artifact.created_at
        if age > self.max_age:
            del self._store[key]
            self.misses += 1
            return None

        self.hits += 1
        return artifact

    def put(self, artifact: CachedArtifact) -> None:
        key = (artifact.correlation_key, artifact.evidence_hash)
        self._store[key] = artifact

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def size(self) -> int:
        return len(self._store)
