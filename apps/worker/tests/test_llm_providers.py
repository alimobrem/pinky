"""LLM provider tests — mock SDK calls, test request shaping and response parsing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pinky_worker.llm.provider import LLMRequest, LLMResponse, ModelTier


async def test_anthropic_provider_complete() -> None:
    mock_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Analysis: OOM detected")],
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
    )
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("pinky_worker.llm.anthropic_provider.AsyncAnthropic", return_value=mock_client):
        from pinky_worker.llm.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key")
        result = await provider.complete(LLMRequest(
            messages=[
                {"role": "system", "content": "You are The Brain."},
                {"role": "user", "content": "Investigate this OOM."},
            ],
            model_tier=ModelTier.REASONING,
            max_tokens=1024,
        ))

    assert isinstance(result, LLMResponse)
    assert result.content == "Analysis: OOM detected"
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.provider == "anthropic"
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["system"] == "You are The Brain."
    assert len(call_kwargs["messages"]) == 1


async def test_anthropic_provider_health_check() -> None:
    with patch("pinky_worker.llm.anthropic_provider.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.api_key = "test-key"
        from pinky_worker.llm.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key")
        assert provider.health_check() is True


async def test_anthropic_provider_no_key() -> None:
    with patch("pinky_worker.llm.anthropic_provider.AsyncAnthropic") as mock_cls:
        mock_cls.return_value.api_key = None
        from pinky_worker.llm.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(api_key=None)
        assert provider.health_check() is False


async def test_vertex_provider_complete() -> None:
    mock_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Vertex analysis result")],
        usage=SimpleNamespace(input_tokens=200, output_tokens=100),
    )
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    mock_vertex_cls = type("AsyncAnthropicVertex", (), {
        "__init__": lambda self, **kw: None,
        "messages": mock_client.messages,
    })

    with patch.object(
        __import__("anthropic"), "AsyncAnthropicVertex", mock_vertex_cls, create=True,
    ):
        from pinky_worker.llm.vertex_provider import VertexProvider

        provider = VertexProvider(project_id="test-project", region="us-east5")
        provider._client = mock_client
        result = await provider.complete(LLMRequest(
            messages=[
                {"role": "system", "content": "Analyze this."},
                {"role": "user", "content": "Evidence here."},
            ],
            model_tier=ModelTier.REASONING,
        ))

    assert isinstance(result, LLMResponse)
    assert result.content == "Vertex analysis result"
    assert result.provider == "vertex"


async def test_vertex_provider_health_check() -> None:
    with patch("anthropic.AsyncAnthropicVertex", create=True):
        from pinky_worker.llm.vertex_provider import VertexProvider

        provider = VertexProvider(project_id="my-project", region="us-east5")
        assert provider.health_check() is True


async def test_vertex_provider_no_project(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    with patch("anthropic.AsyncAnthropicVertex", create=True):
        from pinky_worker.llm.vertex_provider import VertexProvider

        provider = VertexProvider(project_id="", region="us-east5")
        assert provider.health_check() is False
