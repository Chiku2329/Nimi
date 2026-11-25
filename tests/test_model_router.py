import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from model_router import (
    GEMINI_MODELS,
    OPENROUTER_FREE_MODEL,
    OLLAMA_DEFAULT_MODEL,
    ModelRouter,
    is_retryable_provider_error,
)


class ProviderError(Exception):
    def __init__(self, status_code):
        self.status_code = status_code


class DelayedStream:
    def __init__(self, delay):
        self.delay = delay
        self.sent = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.sent:
            raise StopAsyncIteration
        await asyncio.sleep(self.delay)
        self.sent = True
        return SimpleNamespace(choices=[])


class ModelRouterTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, side_effect):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=AsyncMock(side_effect=side_effect))
            )
        )
        return client

    async def test_manually_selected_ollama_is_first(self):
        gemini = self.make_client([object()])
        ollama = self.make_client([object()])
        router = ModelRouter(gemini, ollama_client=ollama)
        self.assertEqual(router.targets("deepseek-v4.1-flash")[0].model, "deepseek-v4.1-flash")

    async def test_manually_selected_openrouter_is_first(self):
        gemini = self.make_client([object()])
        openrouter = self.make_client([object()])
        router = ModelRouter(gemini, openrouter_client=openrouter)
        self.assertEqual(router.targets(OPENROUTER_FREE_MODEL)[0].model, OPENROUTER_FREE_MODEL)

    async def test_primary_gemini_flash_is_first_by_default(self):
        gemini = self.make_client([RuntimeError("unused")])
        router = ModelRouter(gemini)
        self.assertEqual(router.targets()[0].model, "gemini-flash-latest")
        self.assertEqual(router.targets()[1].model, "gemini-flash-lite-latest")

    async def test_rate_limit_falls_back_to_flash_lite(self):
        response = object()
        gemini = self.make_client([ProviderError(429), response])
        router = ModelRouter(gemini)
        result, route = await router.create_completion(messages=[])
        self.assertIs(result, response)
        self.assertIn("gemini-flash-lite-latest", route)
        self.assertEqual(gemini.chat.completions.create.await_count, 2)

    async def test_ollama_is_used_after_gemini_and_before_openrouter(self):
        response = object()
        gemini = self.make_client([ProviderError(429), ProviderError(503)])
        ollama = self.make_client([response])
        openrouter = self.make_client([object()])
        router = ModelRouter(
            gemini,
            openrouter_client=openrouter,
            ollama_client=ollama,
            ollama_model="deepseek-v4.1-flash",
        )
        result, route = await router.create_completion(messages=[])
        self.assertIs(result, response)
        self.assertEqual(route, "Ollama Cloud (DeepSeek V4.1 Flash)")
        self.assertEqual(
            ollama.chat.completions.create.await_args.kwargs["model"],
            "deepseek-v4.1-flash",
        )
        self.assertEqual(openrouter.chat.completions.create.await_count, 0)

    async def test_openrouter_is_used_only_after_both_gemini_and_ollama_fail(self):
        response = object()
        gemini = self.make_client([ProviderError(429), ProviderError(503)])
        ollama = self.make_client([ProviderError(503)])
        openrouter = self.make_client([response])
        router = ModelRouter(
            gemini, openrouter_client=openrouter, ollama_client=ollama
        )
        result, route = await router.create_completion(messages=[])
        self.assertIs(result, response)
        self.assertEqual(route, "OpenRouter Free")
        self.assertEqual(
            ollama.chat.completions.create.await_count, 1
        )
        self.assertEqual(
            openrouter.chat.completions.create.await_args.kwargs["model"],
            OPENROUTER_FREE_MODEL,
        )

    async def test_optional_fallbacks_are_not_configured_without_keys(self):
        router = ModelRouter(self.make_client([]))
        self.assertEqual(len(router.targets()), 2)
        self.assertEqual(OLLAMA_DEFAULT_MODEL, "deepseek-v4.1-flash")

    async def test_authentication_error_does_not_trigger_fallback(self):
        gemini = self.make_client([ProviderError(401)])
        openrouter = self.make_client([object()])
        router = ModelRouter(gemini, openrouter_client=openrouter)
        with self.assertRaises(ProviderError):
            await router.create_completion(messages=[])
        self.assertEqual(openrouter.chat.completions.create.await_count, 0)

    async def test_paid_model_ids_are_never_in_router_targets(self):
        router = ModelRouter(
            self.make_client([]),
            openrouter_client=self.make_client([]),
            ollama_client=self.make_client([]),
        )
        model_ids = [target.model for target in router.targets("paid-model-name")]
        self.assertEqual(
            model_ids,
            [*GEMINI_MODELS, OLLAMA_DEFAULT_MODEL, OPENROUTER_FREE_MODEL],
        )
        self.assertNotIn("paid-model-name", model_ids)

    def test_provider_error_details_include_status_and_safe_message(self):
        from model_router import provider_error_details

        error = ProviderError(401)
        error.body = {"error": {"message": "Invalid API key"}}
        details = provider_error_details(error)
        self.assertIn("status=401", details)
        self.assertIn("Invalid API key", details)

    def test_provider_error_details_redact_credentials_and_bound_message(self):
        from model_router import provider_error_details

        error = ProviderError(403)
        error.body = {
            "error": {
                "message": "Bearer abc.def.ghi api_key=secret-value "
                "sk-1234567890abcdef " + ("x" * 400)
            }
        }
        details = provider_error_details(error)
        self.assertIn("status=403", details)
        self.assertNotIn("abc.def.ghi", details)
        self.assertNotIn("secret-value", details)
        self.assertNotIn("sk-1234567890abcdef", details)
        self.assertLess(len(details), 300)

    def test_only_transient_errors_are_retryable(self):
        for code in (408, 429, 500, 502, 503, 504):
            self.assertTrue(is_retryable_provider_error(ProviderError(code)))
        for code in (400, 401, 403, 404):
            self.assertFalse(is_retryable_provider_error(ProviderError(code)))

    async def test_primary_cooldown_skips_flash_until_cooldown_expires(self):
        gemini = self.make_client([ProviderError(503), object()])
        router = ModelRouter(gemini)
        with patch("model_router.time.monotonic", return_value=1000.0):
            _, route = await router.create_completion(messages=[])
            self.assertIn("gemini-flash-lite-latest", route)
            self.assertEqual(router.targets()[0].model, "gemini-flash-lite-latest")
        with patch("model_router.time.monotonic", return_value=1121.0):
            self.assertEqual(router.targets()[0].model, "gemini-flash-latest")

    async def test_first_chunk_deadline_fails_over_from_stalled_gemini(self):
        gemini = self.make_client([DelayedStream(0.05), DelayedStream(0.05)])
        ollama = self.make_client([DelayedStream(0)])
        router = ModelRouter(gemini, ollama_client=ollama)
        router.first_chunk_timeout_seconds["gemini-flash-latest"] = 0.001
        router.first_chunk_timeout_seconds["gemini-flash-lite-latest"] = 0.001
        router.first_chunk_timeout_seconds[OLLAMA_DEFAULT_MODEL] = 0.1

        received_routes = []
        async for _, route in router.stream_completion(messages=[]):
            received_routes.append(route)

        self.assertEqual(received_routes, ["Ollama Cloud (DeepSeek V4.1 Flash)"])
        self.assertEqual(ollama.chat.completions.create.await_count, 1)

    async def test_primary_timeout_is_shortened_when_client_supports_options(self):
        gemini = self.make_client([])
        gemini.with_options = lambda **kwargs: SimpleNamespace(
            chat=gemini.chat, timeout=kwargs["timeout"]
        )
        router = ModelRouter(gemini)
        self.assertEqual(router.targets()[0].client.timeout, 8.0)
        self.assertIs(router.targets()[1].client, gemini)


if __name__ == "__main__":
    unittest.main()
