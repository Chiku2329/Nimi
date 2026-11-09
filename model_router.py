"""Free-only model failover for Nimi.

Gemini is always the primary provider. OpenRouter is optional and is only
called through the openrouter/free model alias, which routes to free models.
The router buffers a completion before returning it so a failed stream cannot
leave duplicate partial output in the chat.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

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
            "APIConnectionError",
            "APITimeoutError",
            "InternalServerError",
        }
    )


class ModelRouter:
    """Gemini-first router with an optional free-only OpenRouter fallback."""

    def __init__(
        self,
        gemini_client: Any,
        openrouter_api_key: str | None = None,
        openrouter_client: Any | None = None,
    ):
        self.gemini_client = gemini_client
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
        """Return a strict Gemini order followed by the optional free router."""
        preferred = preferred_model if preferred_model in GEMINI_MODELS else GEMINI_MODELS[0]
        order = (preferred,) + tuple(model for model in GEMINI_MODELS if model != preferred)
        targets = [
            ModelTarget(name=f"Google Gemini ({model})", client=self.gemini_client, model=model)
            for model in order
        ]
        if self.openrouter_client is not None:
            # Deliberately hard-coded: never accept a model ID from the user,
            # settings, environment, or an upstream error response here.
            targets.append(
                ModelTarget(
                    name="OpenRouter free fallback",
                    client=self.openrouter_client,
                    model=OPENROUTER_FREE_MODEL,
                )
            )
        return targets

    async def create_completion(self, **kwargs: Any):
        """Try each free target in order and return (response, route label)."""
        params = dict(kwargs)
        params.pop("stream", None)
        preferred = params.pop("model", GEMINI_MODELS[0])
        last_error: Exception | None = None

        for target in self.targets(preferred):
            try:
                response = await target.client.chat.completions.create(
                    **params,
                    model=target.model,
                )
                return response, target.name
            except Exception as error:
                last_error = error
                if not is_retryable_provider_error(error):
                    raise
                print(
                    "model provider temporarily unavailable; trying next free route:",
                    target.name,
                    type(error).__name__,
                    flush=True,
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError("No free model providers are configured.")
