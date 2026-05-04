"""Token and call budgets per execution — prevents runaway LLM costs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutionBudget:
    max_input_tokens: int = 100_000
    max_output_tokens: int = 10_000
    max_calls: int = 10
    used_input_tokens: int = 0
    used_output_tokens: int = 0
    used_calls: int = 0

    def record_call(self, input_tokens: int, output_tokens: int) -> None:
        self.used_input_tokens += input_tokens
        self.used_output_tokens += output_tokens
        self.used_calls += 1

    def check(self) -> str | None:
        if self.used_input_tokens >= self.max_input_tokens:
            return f"Input token budget exceeded: {self.used_input_tokens}/{self.max_input_tokens}"
        if self.used_output_tokens >= self.max_output_tokens:
            return f"Output token budget exceeded: {self.used_output_tokens}/{self.max_output_tokens}"
        if self.used_calls >= self.max_calls:
            return f"Call budget exceeded: {self.used_calls}/{self.max_calls}"
        return None

    @property
    def remaining_input_tokens(self) -> int:
        return max(0, self.max_input_tokens - self.used_input_tokens)

    @property
    def remaining_output_tokens(self) -> int:
        return max(0, self.max_output_tokens - self.used_output_tokens)

    @property
    def total_tokens(self) -> int:
        return self.used_input_tokens + self.used_output_tokens


@dataclass(frozen=True)
class ExecutionTelemetry:
    execution_id: str
    model_tier: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cache_hit: bool
    evidence_hash: str
