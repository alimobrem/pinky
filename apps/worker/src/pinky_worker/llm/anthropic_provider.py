"""Anthropic Claude provider — primary LLM backend for The Brain."""

from __future__ import annotations

import logging
import os
import time
from typing import cast

from anthropic import AsyncAnthropic

from pinky_worker.llm.provider import LLMProviderConfig, LLMRequest, LLMResponse, ModelTier

logger = logging.getLogger(__name__)

DEFAULT_MODEL_MAP: dict[str | ModelTier, str] = {
    ModelTier.UTILITY: "claude-haiku-4-5-20251001",
    ModelTier.INTERACTIVE: "claude-sonnet-4-6",
    ModelTier.REASONING: "claude-opus-4-6",
    ModelTier.SYNTHESIS: "claude-sonnet-4-6",
}


class AnthropicProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model_map: dict[str | ModelTier, str] | None = None,
    ) -> None:
        self._client = AsyncAnthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.config = LLMProviderConfig(
            name="anthropic",
            base_url="https://api.anthropic.com",
            model_map=cast("dict[str | ModelTier, str]", model_map or DEFAULT_MODEL_MAP),
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        model = self.config.model_map.get(request.model_tier, DEFAULT_MODEL_MAP[ModelTier.INTERACTIVE])

        system_msg = None
        messages = []
        for msg in request.messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                messages.append(msg)

        start = time.monotonic()
        response = await self._client.messages.create(
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=system_msg or "",
            messages=messages,
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
            provider="anthropic",
            latency_ms=latency_ms,
        )

    def health_check(self) -> bool:
        return self._client.api_key is not None
