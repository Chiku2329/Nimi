"""Free-only model failover for Nimi.

Gemini is always primary. OpenRouter is optional and hard-pinned to the
openrouter/free alias. Streaming responses are passed through live; failover
is attempted only if a provider fails before it emits its first chunk.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI


GEMINI_MODELS = ("gemini-flash-latest", "gemini-flash-lite-latest")
OPENROUTER_FREE_MODEL = "openrouter/free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class ModelTarget:
    name: str
    client: Any
    model: str


def is_retryable_provider_error(error: Exception) -> bool:
    """Only fail over for temporary capacity, network, or server errors."""
    status = getattr(error, "status_code", None)
    if status is not None:
        return status in {408, 409, 425, 429, 500, 502, 503, 504}
    return (
        isinstance(error, (asyncio.TimeoutError, TimeoutError, httpx.TransportError))
        or error.__class__.__name__ in {
            "APIConnectionError", "APITimeoutError", "InternalServerError"
        }
    )


class ModelRouter:
    """Gemini-first router with optional free-only OpenRouter fallback."""

    def __init__(
        self,
        gemini_client: Any,
        openrouter_api_key: str | None = None,
        openrouter_client: Any | None = None,
    ):
        self.gemini_client = gemini_client
        # A short timeout on the primary prevents a degraded Flash endpoint
        # from holding the user request for the full shared-client timeout.
        self.primary_client = (
            gemini_client.with_options(timeout=8.0)
            if callable(getattr(gemini_client, "with_options", None))
            else gemini_client
        )
        self.primary_cooldown_seconds = 120.0
        self.primary_cooldown_until = 0.0
        self.openrouter_client = openrouter_client
        key = (openrouter_api_key or "").strip()
        if key and self.openrouter_client is None:
            self.openrouter_client = AsyncOpenAI(
                api_key=key,
                base_url=OPENROUTER_BASE_URL,
                timeout=60.0,
                max_retries=0,
            )

    def targets(self, preferred_model: str | None = None) -> list[ModelTarget]:
        preferred = preferred_model if preferred_model in GEMINI_MODELS else GEMINI_MODELS[0]
        order = (preferred,) + tuple(model for model in GEMINI_MODELS if model != preferred)
        cooling_down = time.monotonic() < self.primary_cooldown_until
        if cooling_down:
            order = tuple(model for model in order if model != GEMINI_MODELS[0])
        targets = [
            ModelTarget(
                f"Google Gemini ({model})",
                self.primary_client if model == GEMINI_MODELS[0] else self.gemini_client,
                model,
            )
            for model in order
        ]
        if self.openrouter_client is not None:
            targets.append(
                ModelTarget("OpenRouter free fallback", self.openrouter_client, OPENROUTER_FREE_MODEL)
            )
        return targets

    def _record_provider_failure(self, target: ModelTarget, error: Exception) -> None:
        if target.model == GEMINI_MODELS[0] and is_retryable_provider_error(error):
            self.primary_cooldown_until = time.monotonic() + self.primary_cooldown_seconds
            print(
                f"model circuit open: {target.name} for "
                f"{self.primary_cooldown_seconds:.0f}s after {type(error).__name__}",
                flush=True,
            )

    async def create_completion(self, **kwargs: Any):
        """Non-streaming completion, used for short background tasks such as titles."""
        params = dict(kwargs)
        params.pop("stream", None)
        preferred = params.pop("model", GEMINI_MODELS[0])
        last_error: Exception | None = None
        for target in self.targets(preferred):
            try:
                response = await target.client.chat.completions.create(
                    **params, model=target.model
                )
                return response, target.name
            except Exception as error:
                last_error = error
                if not is_retryable_provider_error(error):
                    raise
                self._record_provider_failure(target, error)
                print(
                    "model provider temporarily unavailable; trying next free route:",
                    target.name, type(error).__name__, flush=True
                )
        if last_error is not None:
            raise last_error
        raise RuntimeError("No free model providers are configured.")

    async def stream_completion(self, **kwargs: Any) -> AsyncIterator[tuple[Any, str]]:
        """Yield provider chunks immediately; retry only before the first chunk."""
        params = dict(kwargs)
        params["stream"] = True
        preferred = params.pop("model", GEMINI_MODELS[0])
        last_error: Exception | None = None
        for target in self.targets(preferred):
            emitted = False
            started_at = time.perf_counter()
            try:
                stream = await target.client.chat.completions.create(
                    **params, model=target.model
                )
                async for chunk in stream:
                    if not emitted:
                        elapsed = time.perf_counter() - started_at
                        print(
                            f"model first chunk: {target.name} after {elapsed:.2f}s",
                            flush=True,
                        )
                    emitted = True
                    yield chunk, target.name
                return
            except Exception as error:
                last_error = error
                elapsed = time.perf_counter() - started_at
                if not emitted:
                    self._record_provider_failure(target, error)
                if emitted or not is_retryable_provider_error(error):
                    print(
                        f"model stream failed: {target.name} after {elapsed:.2f}s "
                        f"({type(error).__name__})",
                        flush=True,
                    )
                    raise
                print(
                    f"model provider unavailable before first chunk: {target.name} "
                    f"after {elapsed:.2f}s ({type(error).__name__}); trying next free route",
                    flush=True,
                )
        if last_error is not None:
            raise last_error
        raise RuntimeError("No free model providers are configured.")
