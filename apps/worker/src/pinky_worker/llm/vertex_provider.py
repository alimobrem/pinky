"""Vertex AI Claude provider — uses Google Cloud Vertex AI to access Claude."""

from __future__ import annotations

import logging
import os
import time

from anthropic import AsyncAnthropicVertex

from pinky_worker.llm.provider import LLMProviderConfig, LLMRequest, LLMResponse, ModelTier

logger = logging.getLogger(__name__)

DEFAULT_MODEL_MAP = {
    ModelTier.UTILITY: "claude-haiku-4-5-20251001",
    ModelTier.INTERACTIVE: "claude-sonnet-4-6",
    ModelTier.REASONING: "claude-sonnet-4-6",
    ModelTier.SYNTHESIS: "claude-sonnet-4-6",
}


class VertexProvider:
    def __init__(
        self,
        project_id: str | None = None,
        region: str | None = None,
        model_map: dict[str, str] | None = None,
    ) -> None:
        self._project_id = project_id or os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "")
        self._region = region or os.environ.get("CLOUD_ML_REGION", "global")
        self._client = AsyncAnthropicVertex(project_id=self._project_id, region=self._region)
        self.config = LLMProviderConfig(
            name="vertex",
            base_url=f"https://{self._region}-aiplatform.googleapis.com",
            model_map=model_map or DEFAULT_MODEL_MAP,
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
            provider="vertex",
            latency_ms=latency_ms,
        )

    def health_check(self) -> bool:
        return bool(self._project_id)
