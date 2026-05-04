"""Provider-agnostic LLM interface with tiered model selection and circuit breaker."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class ModelTier(StrEnum):
    UTILITY = "utility"
    INTERACTIVE = "interactive"
    REASONING = "reasoning"
    SYNTHESIS = "synthesis"


TIER_TIMEOUTS = {
    ModelTier.UTILITY: 15,
    ModelTier.INTERACTIVE: 30,
    ModelTier.REASONING: 120,
    ModelTier.SYNTHESIS: 60,
}


@dataclass(frozen=True)
class LLMRequest:
    messages: list[dict[str, str]]
    model_tier: ModelTier
    max_tokens: int = 4096
    temperature: float = 0.0
    tools: list[dict] | None = None


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    latency_ms: int
    cached: bool = False


@dataclass(frozen=True)
class LLMProviderConfig:
    name: str
    base_url: str
    model_map: dict[str | ModelTier, str]
    max_tokens: int = 4096


@runtime_checkable
class LLMProviderProtocol(Protocol):
    config: LLMProviderConfig

    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    def health_check(self) -> bool: ...


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.state: str = "closed"  # closed, open, half_open

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                return True
            return False
        return True  # half_open allows one attempt


class LLMRouter:
    def __init__(self) -> None:
        self._providers: list[LLMProviderProtocol] = []
        self._breakers: dict[str, CircuitBreaker] = {}

    def register(self, provider: LLMProviderProtocol) -> None:
        self._providers.append(provider)
        self._breakers[provider.config.name] = CircuitBreaker()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        for provider in self._providers:
            breaker = self._breakers[provider.config.name]
            if not breaker.can_execute():
                continue

            try:
                response = await provider.complete(request)
                breaker.record_success()
                return response
            except Exception:
                logger.exception("LLM provider %s failed", provider.config.name)
                breaker.record_failure()
                continue

        raise RuntimeError("All LLM providers unavailable")
