"""Model routing for Nimi with a fast Gemini Flash-Lite default.

Z.AI is an optional selectable route with a bounded timeout. Ollama Cloud remains
manually selectable only; it is never used as an automatic fallback.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI


GEMINI_MODELS = ("gemini-flash-lite-latest", "gemini-flash-latest")
ZAI_DEFAULT_MODEL = "glm-4.7-flash"
ZAI_BASE_URL = "https://api.z.ai/api/paas/v4"
OLLAMA_DEFAULT_MODEL = "deepseek-v4.1-flash"
OLLAMA_BASE_URL = "https://ollama.com/v1"
OPENROUTER_FREE_MODEL = "openrouter/free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class ModelTarget:
    name: str
    client: Any
    model: str


def provider_error_details(error: Exception) -> str:
    """Return bounded provider diagnostics without logging credentials."""
    status = getattr(error, "status_code", None)
    body = getattr(error, "body", None)
    message = ""

    if isinstance(body, dict):
        detail = body.get("error", body)
        if isinstance(detail, dict):
            message = str(
                detail.get("message")
                or detail.get("detail")
                or detail.get("code")
                or detail.get("type")
                or ""
            )
        elif isinstance(detail, str):
            message = detail
    if not message:
        message = str(getattr(error, "message", "") or "")

    # Provider error text is untrusted. Redact common credential formats and
    # credential-labelled values before putting a short excerpt in application logs.
    import re

    message = re.sub(
        r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*",
        "Bearer [REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)\b(api[_-]?key|access[_-]?token|authorization)\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        message,
    )
    message = re.sub(
        r"\b(?:sk|rk|or|ollama)[_-][A-Za-z0-9_-]{8,}\b",
        "[REDACTED]",
        message,
        flags=re.IGNORECASE,
    )
    message = " ".join(message.split())[:240]
    parts = []
    if status is not None:
        parts.append(f"status={status}")
    if message:
        parts.append(f"provider_message={message!r}")
    return " ".join(parts) if parts else f"error_type={type(error).__name__}"


def is_retryable_provider_error(error: Exception) -> bool:
    """Only fail over for temporary capacity, network, or server errors."""
    status = getattr(error, "status_code", None)
    if status is not None:
        return status in {402, 408, 409, 425, 429, 500, 502, 503, 504}
    return (
        isinstance(error, (asyncio.TimeoutError, TimeoutError, httpx.TransportError))
        or error.__class__.__name__ in {
            "APIConnectionError", "APITimeoutError", "InternalServerError"
        }
    )


class ModelRouter:
    """Fast-default router; Ollama Cloud is manual-only to avoid surprise billing."""

    def __init__(
        self,
        gemini_client: Any,
        openrouter_api_key: str | None = None,
        openrouter_client: Any | None = None,
        zai_api_key: str | None = None,
        zai_client: Any | None = None,
        ollama_api_key: str | None = None,
        ollama_model: str = OLLAMA_DEFAULT_MODEL,
        ollama_client: Any | None = None,
    ):
        self.gemini_client = gemini_client
        # A short timeout on the primary prevents a degraded Flash endpoint
        # from holding the user request for the full shared-client timeout.
        self.primary_client = (
            gemini_client.with_options(timeout=3.0)
            if callable(getattr(gemini_client, "with_options", None))
            else gemini_client
        )
        self.fallback_gemini_client = (
            gemini_client.with_options(timeout=4.0)
            if callable(getattr(gemini_client, "with_options", None))
            else gemini_client
        )
        self.primary_cooldown_seconds = 120.0
        self.primary_cooldown_until = 0.0
        self.fallback_cooldown_until = 0.0
        # In-process adaptive stats. Never store prompts, guest IDs, or content.
        self.provider_latency_ema: dict[str, float] = {}
        self.provider_successes: dict[str, int] = {}
        self.provider_failures: dict[str, int] = {}
        self.latency_ema_alpha = 0.35
        self.first_chunk_timeout_seconds = {
            "gemini-flash-lite-latest": 2.5,
            "gemini-flash-latest": 2.5,
            ZAI_DEFAULT_MODEL: 6.0,
            OLLAMA_DEFAULT_MODEL: 12.0,
            OPENROUTER_FREE_MODEL: 4.0,
        }
        self.zai_client = zai_client
        zai_key = (zai_api_key or "").strip()
        if zai_key and self.zai_client is None:
            self.zai_client = AsyncOpenAI(
                api_key=zai_key,
                base_url=ZAI_BASE_URL,
                timeout=7.0,
                max_retries=0,
            )

        self.ollama_client = ollama_client
        ollama_key = (ollama_api_key or "").strip()
        if ollama_key and self.ollama_client is None:
            self.ollama_client = AsyncOpenAI(
                api_key=ollama_key,
                base_url=OLLAMA_BASE_URL,
                timeout=15.0,
                max_retries=0,
            )
        self.ollama_model = (ollama_model or OLLAMA_DEFAULT_MODEL).strip()
        self.first_chunk_timeout_seconds[self.ollama_model] = 12.0

        self.openrouter_client = openrouter_client
        key = (openrouter_api_key or "").strip()
        if key and self.openrouter_client is None:
            self.openrouter_client = AsyncOpenAI(
                api_key=key,
                base_url=OPENROUTER_BASE_URL,
                timeout=5.0,
                max_retries=0,
            )

    def targets(self, preferred_model: str | None = None) -> list[ModelTarget]:
        """Return configured providers, putting an explicitly selected model first."""
        now = time.monotonic()
        targets = [
            ModelTarget(
                f"Google Gemini ({model})",
                self.primary_client if model == GEMINI_MODELS[0] else self.fallback_gemini_client,
                model,
            )
            for index, model in enumerate(GEMINI_MODELS)
            if not (
                (index == 0 and now < self.primary_cooldown_until)
                or (index == 1 and now < self.fallback_cooldown_until)
            )
        ]
        if self.zai_client is not None and preferred_model == ZAI_DEFAULT_MODEL:
            targets.append(
                ModelTarget("Z.AI (GLM-4.7-Flash)", self.zai_client, ZAI_DEFAULT_MODEL)
            )
        if self.ollama_client is not None and preferred_model == self.ollama_model:
            targets.append(
                ModelTarget("Ollama Cloud (DeepSeek V4.1 Flash)", self.ollama_client, self.ollama_model)
            )
        if self.openrouter_client is not None:
            targets.append(
                ModelTarget("OpenRouter Free", self.openrouter_client, OPENROUTER_FREE_MODEL)
            )

        # Adapt free-provider order from recent first-token latency. Keep the
        # safe default order until a provider has at least two successful samples.
        base_rank = {model: index for index, model in enumerate(
            (*GEMINI_MODELS, OPENROUTER_FREE_MODEL)
        )}
        def score(target: ModelTarget) -> tuple[float, int]:
            samples = self.provider_successes.get(target.model, 0)
            rank = base_rank.get(target.model, 99)
            if samples < 2:
                return (float(rank), rank)
            latency = self.provider_latency_ema.get(target.model, 8.0)
            failures = self.provider_failures.get(target.model, 0)
            return (latency + failures * 2.5, rank)
        targets.sort(key=score)

        # Flash-Lite is the default preference, not a lock: let adaptive
        # metrics choose among free automatic routes after enough samples.
        # Any other explicit selection (Flash, OpenRouter, Z.AI, Ollama) stays
        # first so the model selector continues to behave predictably.
        if preferred_model != GEMINI_MODELS[0]:
            selected = next(
                (target for target in targets if target.model == preferred_model), None
            )
            if selected is not None:
                targets.remove(selected)
                targets.insert(0, selected)
        return targets

    def _record_provider_success(self, target: ModelTarget, first_token_seconds: float) -> None:
        model = target.model
        previous = self.provider_latency_ema.get(model)
        alpha = self.latency_ema_alpha
        self.provider_latency_ema[model] = (
            first_token_seconds if previous is None
            else alpha * first_token_seconds + (1.0 - alpha) * previous
        )
        self.provider_successes[model] = self.provider_successes.get(model, 0) + 1
        self.provider_failures[model] = max(0, self.provider_failures.get(model, 0) - 1)

    def _record_provider_failure(self, target: ModelTarget, error: Exception) -> None:
        self.provider_failures[target.model] = min(
            8, self.provider_failures.get(target.model, 0) + 1
        )
        if target.model in GEMINI_MODELS and is_retryable_provider_error(error):
            cooldown_until = time.monotonic() + self.primary_cooldown_seconds
            if target.model == GEMINI_MODELS[0]:
                self.primary_cooldown_until = cooldown_until
            else:
                self.fallback_cooldown_until = cooldown_until
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
                    target.name, provider_error_details(error), flush=True
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
                iterator = stream.__aiter__()
                try:
                    first_chunk = await asyncio.wait_for(
                        iterator.__anext__(),
                        timeout=self.first_chunk_timeout_seconds.get(target.model, 12.0),
                    )
                except StopAsyncIteration:
                    return
                except asyncio.TimeoutError:
                    close_stream = (
                        getattr(stream, "close", None)
                        or getattr(stream, "aclose", None)
                    )
                    if callable(close_stream):
                        try:
                            await close_stream()
                        except Exception as close_error:
                            print(
                                "model stream cleanup failed:",
                                type(close_error).__name__,
                                flush=True,
                            )
                    raise
                elapsed = time.perf_counter() - started_at
                self._record_provider_success(target, elapsed)
                print(
                    f"model first chunk: {target.name} after {elapsed:.2f}s",
                    flush=True,
                )
                emitted = True
                yield first_chunk, target.name
                async for chunk in iterator:
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
                        f"({type(error).__name__}; {provider_error_details(error)})",
                        flush=True,
                    )
                    raise
                print(
                    f"model provider unavailable before first chunk: {target.name} "
                    f"after {elapsed:.2f}s ({type(error).__name__}; "
                    f"{provider_error_details(error)}); trying next free route",
                    flush=True,
                )
        if last_error is not None:
            raise last_error
        raise RuntimeError("No free model providers are configured.")
