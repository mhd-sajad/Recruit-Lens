"""
Tests for LLM provider abstraction, token-bucket rate limiter, SQLite cache, and fallback chain.
"""

from pathlib import Path

import pytest

from app.llm.provider import (
    BaseLLMProvider,
    FallbackLLMProvider,
    LLMCache,
    LLMResponse,
    NoLLMProvider,
    TokenBucketRateLimiter,
)


class MockSuccessProvider(BaseLLMProvider):
    def __init__(self, name: str = "mock_success", content: str = '{"status": "ok"}'):
        self._name = name
        self.content = content
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return self._name

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            content=self.content,
            prompt_tokens=15,
            completion_tokens=10,
            model=self._name,
            cached=False,
            latency_ms=12.0,
        )


class MockFailingProvider(BaseLLMProvider):
    def __init__(
        self, name: str = "mock_failing", error_msg: str = "Simulated 429 quota exhausted"
    ):
        self._name = name
        self.error_msg = error_msg
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return self._name

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        self.call_count += 1
        raise RuntimeError(self.error_msg)


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter() -> None:
    """Verify rate limiter permits requests within capacity."""
    limiter = TokenBucketRateLimiter(max_rpm=60, max_tpm=6000)
    assert limiter.available_requests == 60.0

    # Acquire 500 tokens
    await limiter.acquire(500)
    assert limiter.available_requests < 60.0
    assert limiter.available_tokens <= 5500.0


def test_sqlite_llm_cache(tmp_path: Path) -> None:
    """Verify persistent caching by model, prompt, and system prompt."""
    db_file = tmp_path / "test_cache.sqlite"
    cache = LLMCache(db_file)

    # Miss
    assert cache.get("model_a", "sys", "hello", 0.1) is None

    # Set
    resp = LLMResponse(
        content='{"msg": "cached"}',
        prompt_tokens=20,
        completion_tokens=10,
        model="model_a",
    )
    cache.set("model_a", "sys", "hello", 0.1, resp)

    # Hit
    cached_hit = cache.get("model_a", "sys", "hello", 0.1)
    assert cached_hit is not None
    assert cached_hit.content == '{"msg": "cached"}'
    assert cached_hit.cached is True

    # Different prompt is a Miss
    assert cache.get("model_a", "sys", "goodbye", 0.1) is None


@pytest.mark.asyncio
async def test_fallback_provider_chain() -> None:
    """Verify FallbackLLMProvider fails over when primary provider fails."""
    failing = MockFailingProvider("primary_failing")
    success = MockSuccessProvider("secondary_success", '{"result": "fallback_worked"}')

    fallback_chain = FallbackLLMProvider([failing, success])

    resp = await fallback_chain.complete("Test prompt")
    assert resp.content == '{"result": "fallback_worked"}'
    assert failing.call_count == 1
    assert success.call_count == 1
    assert fallback_chain.provider_name == "secondary_success"


@pytest.mark.asyncio
async def test_no_llm_provider_raises() -> None:
    """Verify NoLLMProvider raises RuntimeError to trigger template fallback."""
    provider = NoLLMProvider()
    with pytest.raises(RuntimeError, match="No-LLM mode active"):
        await provider.complete("Test prompt")


@pytest.mark.asyncio
async def test_groq_cloud_provider_mocked_success(tmp_path: Path) -> None:
    """Verify GroqProvider completes successfully, parses usage, and caches."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.llm.provider import GroqProvider

    cache = LLMCache(tmp_path / "groq_cache.sqlite")
    provider = GroqProvider(api_key="gsk_mock_test_key_12345", cache=cache)
    provider._active_models = ["qwen/qwen3.8-27b"]

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "choices": [{"message": {"content": '{"analysis": "strong fit"}'}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_resp
        resp = await provider.complete("Evaluate candidate", system_prompt="System prompt")
        assert resp.content == '{"analysis": "strong fit"}'
        assert resp.prompt_tokens == 120
        assert resp.completion_tokens == 45
        assert resp.cached is False

        # Cached hit on identical prompt
        cached_resp = await provider.complete("Evaluate candidate", system_prompt="System prompt")
        assert cached_resp.content == '{"analysis": "strong fit"}'
        assert cached_resp.cached is True
        assert mock_post.call_count == 1  # No second HTTP call


@pytest.mark.asyncio
async def test_groq_cloud_provider_error_handling() -> None:
    """Verify GroqProvider raises on empty key and handles 429 retries."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.llm.provider import GroqProvider

    # Empty key raises ValueError
    empty_provider = GroqProvider(api_key="")
    with pytest.raises(ValueError, match="not configured"):
        await empty_provider.complete("Hello")

    # 429 with short retry
    provider = GroqProvider(api_key="gsk_test")
    provider.cache = None
    provider._active_models = ["qwen/qwen3.8-27b"]

    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"retry-after": "0.01"}

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [{"message": {"content": '{"ok": true}'}}],
        "usage": {"total_tokens": 20, "prompt_tokens": 10, "completion_tokens": 10},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [resp_429, resp_200]
        resp = await provider.complete("Retry prompt")
        assert resp.content == '{"ok": true}'
        assert mock_post.call_count == 2
