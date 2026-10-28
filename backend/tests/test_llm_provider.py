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
