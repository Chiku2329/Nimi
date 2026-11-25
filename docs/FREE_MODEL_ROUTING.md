# Nimi free model routing

## Provider order

1. Google Gemini Flash (gemini-flash-latest) is the default primary model.
2. Google Gemini Flash-Lite (gemini-flash-lite-latest) is the first fallback.
3. Z.AI GLM-4.7-Flash (glm-4.7-flash) is the next optional free fallback.
4. Ollama Cloud is optional and remains disabled unless its key is configured.
5. OpenRouter's openrouter/free route is the final fallback and may only select free models.

Z.AI uses the OpenAI-compatible endpoint `https://api.z.ai/api/paas/v4`. Its
official pricing lists GLM-4.7-Flash as free for input, cached input, and output.
Do not substitute GLM-4.7-FlashX; that is a paid model.

## No-paid-model guarantee

Nimi never accepts an OpenRouter model ID from a user setting or environment
variable. The fallback model is hard-coded as openrouter/free; no paid model
route or paid-model retry is configured. Z.AI is hard-coded to glm-4.7-flash.
Do not replace either with a paid model.

## Failover behavior

- Retry/fail over on rate limits (429), transient network/timeouts, and temporary
  provider/server errors (408, 409, 425, 5xx).
- A 402 payment/quota response marks that provider unavailable for the current
  request and moves to the next configured free provider; it is not retried
  against the same provider.
- Do not fail over on authentication, permission, malformed-request, or other
  client errors (for example 400, 401, 403, 404).
- Responses are streamed live; failover is attempted only if a provider fails
  before its first chunk.
- Tool calls use the same provider order and server-side tool allowlists.
- If all free providers are unavailable, Nimi returns its existing friendly
  temporary-error message. No paid provider is attempted.

## Required environment variables

- API_KEY: existing Google Gemini API key (unchanged).
- ZAI_API_KEY: optional Z.AI API key. When set, enables GLM-4.7-Flash.
- OLLAMA_API_KEY: optional Ollama Cloud key. Leave unset to disable it.
- OPENROUTER_API_KEY: optional OpenRouter API key. Leave unset to disable it.

All keys are server-side secrets. Never put them in source control or expose
them to the browser.

## Operational limitations

Free quotas and rate limits may change. Gemini quotas are project-level and
vary by model and usage tier. Z.AI's public pricing page lists GLM-4.7-Flash
token usage as free; account-level rate limits may still apply. OpenRouter's
free route is also rate-limited and its available free models can change.
This feature improves resilience; it cannot guarantee uninterrupted inference.
