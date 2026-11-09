# Nimi free model routing

## Provider order

1. Google Gemini Flash (gemini-flash-latest) is the default primary model.
2. Google Gemini Flash-Lite (gemini-flash-lite-latest) is the first fallback.
3. OpenRouter's openrouter/free route is the final fallback and may only select free models.

The existing Gemini OpenAI-compatible integration remains in place. The OpenRouter
provider is optional and is enabled only when the server environment contains
OPENROUTER_API_KEY. No key is required to keep using Gemini.

## No-paid-model guarantee

Nimi never accepts an OpenRouter model ID from a user setting or environment
variable. The fallback model is hard-coded as openrouter/free; no paid model
route or paid-model retry is configured. Do not replace this with OpenRouter's
paid auto-router.

## Failover behavior

- Retry/fail over on rate limits (429), transient network/timeouts, and temporary
  provider/server errors (408, 409, 425, 5xx).
- Do not fail over on authentication, permission, malformed-request, or other
  client errors (for example 400, 401, 403, 404).
- Responses are buffered before being streamed into Chainlit. This avoids
  duplicate partial answers if a provider fails midway through generation.
- Tool calls use the same provider order and server-side tool allowlists.
- If all free providers are unavailable, Nimi returns its existing friendly
  temporary-error message. No paid provider is attempted.

## Required environment variables

- API_KEY: existing Google Gemini API key (unchanged).
- OPENROUTER_API_KEY: optional OpenRouter API key. Leave unset to disable
  cross-provider fallback.

Never put either key in source control or expose it to the browser.

## Operational limitations

Free quotas are finite and may change. Gemini quotas are project-level and vary
by model and usage tier. OpenRouter's free route is also rate-limited and its
available free models can change. This feature improves resilience; it cannot
guarantee uninterrupted or unlimited free inference.
