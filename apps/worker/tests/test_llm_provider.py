import time

import pytest

from pinky_worker.llm.provider import (
    CircuitBreaker,
    LLMProviderConfig,
    LLMRequest,
    LLMResponse,
    LLMRouter,
    ModelTier,
    TIER_TIMEOUTS,
)


def test_model_tier_timeouts() -> None:
    assert TIER_TIMEOUTS[ModelTier.UTILITY] == 15
    assert TIER_TIMEOUTS[ModelTier.REASONING] == 120
    assert TIER_TIMEOUTS[ModelTier.SYNTHESIS] == 60
    assert TIER_TIMEOUTS[ModelTier.INTERACTIVE] == 30


def test_circuit_breaker_starts_closed() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.state == "closed"
    assert cb.can_execute()


def test_circuit_breaker_opens_after_threshold() -> None:
    cb = CircuitBreaker(failure_threshold=2)
    cb.record_failure()
    assert cb.can_execute()
    cb.record_failure()
    assert cb.state == "open"
    assert not cb.can_execute()


def test_circuit_breaker_recovers_after_timeout() -> None:
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
    cb.record_failure()
    assert cb.state == "open"
    time.sleep(0.01)
    assert cb.can_execute()
    assert cb.state == "half_open"


def test_circuit_breaker_resets_on_success() -> None:
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.failure_count == 0
    assert cb.state == "closed"


@pytest.mark.asyncio
async def test_llm_router_raises_when_all_providers_down() -> None:
    router = LLMRouter()
    request = LLMRequest(messages=[{"role": "user", "content": "test"}], model_tier=ModelTier.UTILITY)
    with pytest.raises(RuntimeError, match="All LLM providers unavailable"):
        await router.complete(request)
