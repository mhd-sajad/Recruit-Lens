"""
LLM Provider Interface and Concrete Implementations (Groq, Ollama, Fallback).

Features:
- Dynamic model discovery from Groq /models endpoint.
- Asynchronous token-bucket rate limiter matching free-tier TPM and RPM.
- SHA-256 persistent SQLite response cache to conserve quota.
- Automatic exponential backoff with jitter on HTTP 429/503.
- Resilient fallback chain: Groq -> Ollama -> NoLLM.
"""

import abc
import asyncio
import hashlib
import random
import sqlite3
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.logging import get_logger

logger = get_logger("llm.provider")


class LLMResponse:
    """Standardized response from any LLM provider."""

    def __init__(
        self,
        content: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: str = "unknown",
        cached: bool = False,
        latency_ms: float = 0.0,
    ):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.model = model
        self.cached = cached
        self.latency_ms = latency_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "cached": self.cached,
            "latency_ms": self.latency_ms,
        }


class TokenBucketRateLimiter:
    """
    Asynchronous token-bucket rate limiter enforcing both Requests-Per-Minute (RPM)
    and Tokens-Per-Minute (TPM) limits for free-tier providers.
    """

    def __init__(self, max_rpm: int = 30, max_tpm: int = 7000):
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm

        self.available_requests = float(max_rpm)
        self.available_tokens = float(max_tpm)

        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.last_refill = now

        # Refill proportional to elapsed fraction of a minute (60 seconds)
        refill_fraction = elapsed / 60.0
        self.available_requests = min(
            float(self.max_rpm), self.available_requests + (self.max_rpm * refill_fraction)
        )
        self.available_tokens = min(
            float(self.max_tpm), self.available_tokens + (self.max_tpm * refill_fraction)
        )

    async def acquire(self, estimated_tokens: int = 500) -> None:
        """Wait until sufficient request and token quota are available."""
        while True:
            async with self._lock:
                self._refill()
                if self.available_requests >= 1.0 and self.available_tokens >= estimated_tokens:
                    self.available_requests -= 1.0
                    self.available_tokens -= estimated_tokens
                    return

                # Calculate minimum wait time
                req_wait = (
                    (1.0 - self.available_requests) / (self.max_rpm / 60.0)
                    if self.available_requests < 1.0
                    else 0.0
                )
                tok_wait = (
                    (estimated_tokens - self.available_tokens) / (self.max_tpm / 60.0)
                    if self.available_tokens < estimated_tokens
                    else 0.0
                )
                wait_time = max(0.1, max(req_wait, tok_wait))

            await asyncio.sleep(min(wait_time, 2.0))

    def release(self, unused_tokens: int) -> None:
        """Refund unused estimated tokens back to the bucket."""
        if unused_tokens > 0:
            self.available_tokens = min(float(self.max_tpm), self.available_tokens + unused_tokens)


class LLMCache:
    """Persistent SQLite-backed cache keyed by SHA-256 hash of query parameters."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = settings.data_dir / "llm_cache.sqlite"
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_cache (
                    cache_key TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    content TEXT NOT NULL,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    created_at REAL
                )
                """
            )
            conn.commit()

    def _make_key(
        self, model: str, system_prompt: str, user_prompt: str, temperature: float
    ) -> str:
        payload = f"{model}:{system_prompt}:{user_prompt}:{temperature:.2f}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(
        self, model: str, system_prompt: str, user_prompt: str, temperature: float
    ) -> LLMResponse | None:
        key = self._make_key(model, system_prompt, user_prompt, temperature)
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content, prompt_tokens, completion_tokens FROM response_cache WHERE cache_key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                if row:
                    return LLMResponse(
                        content=row[0],
                        prompt_tokens=row[1],
                        completion_tokens=row[2],
                        model=model,
                        cached=True,
                        latency_ms=0.5,
                    )
        except Exception as e:
            logger.warning(f"LLM cache read error: {e}")
        return None

    def set(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        response: LLMResponse,
    ) -> None:
        key = self._make_key(model, system_prompt, user_prompt, temperature)
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO response_cache
                    (cache_key, model, content, prompt_tokens, completion_tokens, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        model,
                        response.content,
                        response.prompt_tokens,
                        response.completion_tokens,
                        time.time(),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"LLM cache write error: {e}")


class BaseLLMProvider(abc.ABC):
    """Abstract base class for all LLM providers."""

    @abc.abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        """Generate a completion for the given prompt and system instructions."""
        pass

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        pass


class GroqProvider(BaseLLMProvider):
    """Production provider connecting to Groq free-tier API with rate-limiting and caching."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        cache: LLMCache | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.cache = cache or (LLMCache() if settings.LLM_CACHE_ENABLED else None)
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(
            max_rpm=settings.LLM_MAX_RPM, max_tpm=settings.LLM_MAX_TPM
        )
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self._active_models: list[str] | None = None

    @property
    def provider_name(self) -> str:
        return "groq"

    async def _discover_model(self, client: httpx.AsyncClient) -> str:
        """Query Groq /models endpoint to pick an active model."""
        if self._active_models is not None:
            return self.model

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = await client.get(
                "https://api.groq.com/openai/v1/models", headers=headers, timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                active = [
                    m["id"]
                    for m in data.get("data", [])
                    if m.get("active", True) and not m["id"].startswith("whisper")
                ]
                self._active_models = active
                # If current model in active, keep it; else fallback
                if self.model not in active:
                    for fallback in [
                        settings.GROQ_FALLBACK_MODEL,
                        "openai/gpt-oss-120b",
                        "openai/gpt-oss-20b",
                        "qwen/qwen3.8-27b",
                    ]:
                        if fallback in active:
                            self.model = fallback
                            break
                    else:
                        if active:
                            self.model = active[0]
        except Exception as e:
            logger.warning(f"Could not discover Groq models: {e}. Keeping default {self.model}")

        return self.model

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        if not self.api_key.strip():
            raise ValueError("Groq API key is not configured.")

        # Check cache
        if self.cache:
            cached_resp = self.cache.get(self.model, system_prompt, prompt, temperature)
            if cached_resp:
                return cached_resp

        estimated_tokens = (len(prompt) + len(system_prompt)) // 4 + min(350, max_tokens)
        await self.rate_limiter.acquire(estimated_tokens)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        start_time = time.monotonic()
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS) as client:
            await self._discover_model(client)
            payload["model"] = self.model

            for attempt in range(settings.LLM_MAX_RETRIES + 1):
                try:
                    resp = await client.post(self.endpoint, headers=headers, json=payload)
                    latency_ms = (time.monotonic() - start_time) * 1000.0

                    if resp.status_code == 200:
                        data = resp.json()
                        choice = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        total_used = usage.get("total_tokens", 0)
                        if total_used > 0 and total_used < estimated_tokens:
                            self.rate_limiter.release(estimated_tokens - total_used)
                        llm_resp = LLMResponse(
                            content=choice,
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            model=self.model,
                            cached=False,
                            latency_ms=latency_ms,
                        )
                        if self.cache:
                            self.cache.set(self.model, system_prompt, prompt, temperature, llm_resp)
                        return llm_resp

                    # If rate limited (429) or temporary server error (503), back off with jitter
                    if resp.status_code in (429, 503):
                        retry_after = float(resp.headers.get("retry-after", "2.0"))
                        chat_pool = [
                            "qwen/qwen3.8-27b",
                            "openai/gpt-oss-120b",
                            "openai/gpt-oss-20b",
                        ]
                        if retry_after > 15.0:
                            current_idx = (
                                chat_pool.index(self.model) if self.model in chat_pool else -1
                            )
                            next_model = chat_pool[(current_idx + 1) % len(chat_pool)]
                            if next_model != self.model and attempt < len(chat_pool):
                                logger.warning(
                                    f"Groq 429 on model {self.model} with long cooldown ({retry_after:.1f}s). Switching to fallback model {next_model}"
                                )
                                self.model = next_model
                                payload["model"] = self.model
                                continue

                        # Cap backoff to max 15.0s to respect performance bounds
                        jitter = random.uniform(0.5, 1.5)
                        backoff = min(15.0, max(retry_after, (2**attempt) * jitter))
                        logger.warning(
                            f"Groq {resp.status_code} on model {self.model}. Backing off {backoff:.2f}s (attempt {attempt + 1})"
                        )
                        await asyncio.sleep(backoff)
                        continue

                    # If model not found or forbidden, attempt fallback model
                    if resp.status_code in (404, 400) and attempt == 0:
                        logger.warning(
                            f"Groq model {self.model} error ({resp.status_code}): {resp.text}. Falling back to {settings.GROQ_FALLBACK_MODEL}"
                        )
                        self.model = settings.GROQ_FALLBACK_MODEL
                        payload["model"] = self.model
                        continue

                    resp.raise_for_status()

                except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                    last_error = net_err
                    logger.warning(f"Network error calling Groq: {net_err}. Attempt {attempt + 1}")
                    await asyncio.sleep((2**attempt) * random.uniform(0.5, 1.0))
                except Exception as ex:
                    last_error = ex
                    logger.error(f"Unexpected error calling Groq: {ex}")
                    break

        raise RuntimeError(f"Groq completion failed after retries: {last_error}")


class OllamaProvider(BaseLLMProvider):
    """Local provider connecting to Ollama HTTP API."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        endpoint = f"{self.base_url}/api/chat"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if json_mode:
            payload["format"] = "json"

        start_time = time.monotonic()
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            latency_ms = (time.monotonic() - start_time) * 1000.0

            content = data.get("message", {}).get("content", "")
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)

            return LLMResponse(
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=self.model,
                cached=False,
                latency_ms=latency_ms,
            )


class NoLLMProvider(BaseLLMProvider):
    """Deterministic fallback provider that signals no external LLM is available."""

    @property
    def provider_name(self) -> str:
        return "no_llm"

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        raise RuntimeError("No-LLM mode active. System must route to deterministic templates.")


class FallbackLLMProvider(BaseLLMProvider):
    """
    Chained provider that attempts providers in order:
    Primary (e.g. Groq) -> Secondary (e.g. Ollama) -> Fallback (NoLLMProvider).
    """

    def __init__(self, providers: list[BaseLLMProvider] | None = None):
        if providers is None:
            providers = []
            if settings.GROQ_API_KEY.strip():
                providers.append(GroqProvider())
            providers.append(OllamaProvider())
            providers.append(NoLLMProvider())
        self.providers = providers
        self.active_provider_name = self.providers[0].provider_name if self.providers else "none"

    @property
    def provider_name(self) -> str:
        return self.active_provider_name

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        errors = []
        for provider in self.providers:
            try:
                resp = await provider.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    json_mode=json_mode,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                self.active_provider_name = provider.provider_name
                return resp
            except Exception as e:
                errors.append(f"{provider.provider_name}: {e}")
                logger.warning(
                    f"Provider {provider.provider_name} failed: {e}. Trying next in fallback chain."
                )

        raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")
