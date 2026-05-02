from datetime import datetime, timedelta, timezone

from pinky_worker.llm.cache import ArtifactCache, CachedArtifact


def _artifact(correlation_key: str = "ck1", evidence_hash: str = "eh1", age_minutes: int = 0) -> CachedArtifact:
    created = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    return CachedArtifact(
        artifact_id="a1",
        correlation_key=correlation_key,
        evidence_hash=evidence_hash,
        summary="test",
        recommended_action="fix it",
        confidence=0.9,
        tool_calls=["kubectl-get"],
        created_at=created,
    )


def test_cache_hit() -> None:
    cache = ArtifactCache()
    cache.put(_artifact())
    result = cache.get("ck1", "eh1")
    assert result is not None
    assert result.artifact_id == "a1"
    assert cache.hits == 1
    assert cache.misses == 0


def test_cache_miss_different_hash() -> None:
    cache = ArtifactCache()
    cache.put(_artifact(evidence_hash="eh1"))
    result = cache.get("ck1", "eh2")
    assert result is None
    assert cache.misses == 1


def test_cache_miss_different_key() -> None:
    cache = ArtifactCache()
    cache.put(_artifact(correlation_key="ck1"))
    result = cache.get("ck2", "eh1")
    assert result is None


def test_cache_expires_old_artifacts() -> None:
    cache = ArtifactCache(max_age=timedelta(minutes=30))
    cache.put(_artifact(age_minutes=60))
    result = cache.get("ck1", "eh1")
    assert result is None
    assert cache.misses == 1


def test_cache_hit_rate() -> None:
    cache = ArtifactCache()
    cache.put(_artifact())
    cache.get("ck1", "eh1")  # hit
    cache.get("ck1", "eh1")  # hit
    cache.get("ck2", "eh2")  # miss
    assert cache.hit_rate == 2 / 3
