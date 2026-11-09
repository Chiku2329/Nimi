import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from model_router import (
    GEMINI_MODELS,
    OPENROUTER_FREE_MODEL,
    ModelRouter,
    is_retryable_provider_error,
)


class ProviderError(Exception):
    def __init__(self, status_code):
        self.status_code = status_code


class ModelRouterTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, side_effect):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=AsyncMock(side_effect=side_effect))
            )
        )
        return client

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

    async def test_openrouter_is_used_only_after_both_gemini_models_fail(self):
        response = object()
        gemini = self.make_client([ProviderError(429), ProviderError(503)])
        openrouter = self.make_client([response])
        router = ModelRouter(gemini, openrouter_client=openrouter)
        result, route = await router.create_completion(messages=[])
        self.assertIs(result, response)
        self.assertEqual(route, "OpenRouter free fallback")
        self.assertEqual(
            openrouter.chat.completions.create.await_args.kwargs["model"],
            OPENROUTER_FREE_MODEL,
        )

    async def test_openrouter_is_not_configured_without_a_key_or_client(self):
        router = ModelRouter(self.make_client([]))
        self.assertEqual(len(router.targets()), 2)

    async def test_authentication_error_does_not_trigger_fallback(self):
        gemini = self.make_client([ProviderError(401)])
        openrouter = self.make_client([object()])
        router = ModelRouter(gemini, openrouter_client=openrouter)
        with self.assertRaises(ProviderError):
            await router.create_completion(messages=[])
        self.assertEqual(openrouter.chat.completions.create.await_count, 0)

    async def test_paid_model_ids_are_never_in_router_targets(self):
        router = ModelRouter(self.make_client([]), openrouter_client=self.make_client([]))
        model_ids = [target.model for target in router.targets("paid-model-name")]
        self.assertEqual(model_ids, [*GEMINI_MODELS, OPENROUTER_FREE_MODEL])
        self.assertNotIn("paid-model-name", model_ids)

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
