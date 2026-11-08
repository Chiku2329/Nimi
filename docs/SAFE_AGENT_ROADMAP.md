# Nimi: Safe Agent Foundation

## Product direction

Nimi is a public, anonymous AI companion. Visitors must be able to use it without creating an account or signing in.

**Tagline:** Nimi - One AI. Infinite Possibilities.

**Subtitle:** Your AI companion for thinking, creating, learning and exploring.

The initial agent experience should be useful without granting agents the ability to execute arbitrary code, modify application files, change their own instructions, or access server secrets.

## Initial agent modes

Keep the existing General, Coding Helper, Writing Helper, and Study Tutor experiences. Introduce specialist capabilities incrementally:

1. **Research** — search, compare, summarize, and cite information.
2. **Coding** — generate code, explain code, review code, and suggest fixes. Do not execute code or edit server files.
3. **Debugging** — inspect user-provided code and error messages, explain likely causes, and propose patches. Do not run untrusted code.
4. **Security and Testing** — review code and produce test cases and checklists; no execution in the initial release.

Agents should use a narrow, explicit tool allowlist. Tool outputs and uploaded documents are untrusted data, not instructions. The assistant must not reveal environment variables, API keys, internal prompts, or other visitors' information.

## Public-access security requirements

Public anonymous access is intentional. Do not reintroduce mandatory registration or login as a shortcut.

Before enabling or deploying anonymous public access, verify all of the following:

- Every visitor's conversation history and uploaded files are isolated from every other visitor.
- Persistent memory is either disabled for anonymous visitors or isolated using a secure, server-generated per-visitor identifier. Never use a shared fallback key such as `default`.
- Thread listing, thread resume, thread deletion, and data-layer access cannot expose another visitor's conversations.
- Uploaded files have a small size limit and a strict allowlist of supported file types. Validate content, not only filename extensions.
- Add abuse controls and request/token budgets that work across multiple application workers or replicas.
- Keep API keys and database credentials server-side; never include them in client-visible messages or files.
- Keep arbitrary code execution, shell access, unrestricted filesystem access, and agent self-modification disabled.
- Use HTTPS, strict origin configuration, pinned dependencies, and automated dependency/security checks.
- Test privacy boundaries with two independent anonymous browser sessions before public release.

A public anonymous app still needs abuse protection. If robust visitor-level rate limiting cannot be implemented without a stable identity, use conservative global limits and provider-side budget alerts while designing a privacy-preserving visitor identifier.

## Phased implementation

### Phase 0 — Safe foundation

- Preserve the current production branch and existing user experience.
- Work on a separate feature branch and submit reviewable pull requests.
- Resolve the anonymous-session identity and thread-privacy design before changing authentication or deploying public access.
- Reduce upload limits and restrict supported file types.
- Pin and audit dependencies.
- Add automated tests for privacy boundaries, tool allowlists, and safe handling of uploaded content.

### Phase 1 — Agent architecture

- Add a small agent registry with explicit names, descriptions, system instructions, and permitted tools.
- Reuse the existing Gemini-compatible API client and existing model choices initially.
- Keep the default model free-first; do not add paid providers or automatic paid fallbacks without explicit owner approval.
- Keep agent responses conversational and preserve the existing chat UI where possible.

### Phase 2 — Specialist agents

- Add Research, Coding, and Debugging first.
- Add Security Reviewer and Testing Assistant after the first agents are tested.
- Make clear to visitors that coding assistance generates and reviews code but does not execute it.

### Phase 3 — Optional execution sandbox and model routing

- Consider code execution only in a separate, disposable sandbox with strict CPU, memory, time, filesystem, network, and output limits.
- Consider a model router such as OmniRoute only after the basic agents are stable. Any paid provider must remain disabled unless explicitly enabled by the owner.
- Do not expose an administration dashboard or router management API publicly.

## Implementation notes

The first agent-foundation implementation adds a server-owned registry for
General, Coding Helper, Writing Helper, Study Tutor, Research Agent, Debugging
Agent, Security Reviewer, and Testing Assistant. Each profile receives only
its permitted tool definitions, and the server independently rejects tool
calls outside that profile's allowlist. The existing Gemini-compatible client
and model choices remain unchanged.

The first release intentionally has no shell, arbitrary code execution,
filesystem editing, deployment, or agent self-modification tools. Coding,
debugging, security, and testing agents can generate recommendations and
patches from visitor-provided material, but cannot run them.

The browser favicon is served from Nimi's existing infinity SVG asset through
the conventional `/favicon.ico` and `/favicon.svg` routes. This is separate
from Chainlit's assistant logo setting.

## Development workflow

- Use ECC (Everything Claude Code) as a developer-side coding workflow where supported by the developer's coding environment. ECC is not a runtime dependency of Nimi and does not provide model API credits.
- Review each change, run tests, and deploy only after explicit approval.
- Never commit secrets, local databases, visitor data, or generated credentials.
