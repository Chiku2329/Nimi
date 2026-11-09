# Nimi production-readiness audit

## Scope

Reviewed the staging branch for guest identity and isolation, request limits, tool permissions, model routing, upload validation, private attachment storage, persistent data paths, browser response headers, container permissions, database initialization, and CI security checks.

This is a code/configuration review, not a penetration test, provider certification, or verification of Blitz account settings.

## Findings and changes in this audit

### Fixed: silent fallback from persistent storage

The app and database initializer previously fell back to the current application directory when `DATA_DIR` could not be created or written. On a hosted deployment, this can make chat data, memories, rate-limit state, and attachment blobs land outside the persistent volume without an obvious startup failure.

The new `data_directory.resolve_data_dir()` probes the configured directory and fails startup with a clear error if it is unavailable. The app, SQLite initializer, and SQLite rate limiter now use the same resolved path. Local development still defaults to the current working directory when `DATA_DIR` is not set.

### Existing controls confirmed in code

- Guest identities use signed, expiring, HttpOnly, Secure, SameSite=Lax cookies; invalid or expired cookies are rejected.
- Rate limits are enforced per guest and globally, and database errors fail closed.
- Agent profiles use server-side tool allowlists. No shell, code execution, filesystem, or self-modification tools are exposed.
- Model routing is pinned to Gemini Flash, Gemini Flash-Lite, and optional OpenRouter `openrouter/free`; arbitrary or paid model IDs are not accepted by the router.
- Upload handling bounds file count, size, extracted text, PDF pages, and image pixel count, and validates supported content types.
- Attachment reads require short-lived HMAC-signed URLs; object keys are path-validated and responses are marked private/no-store.
- Browser security headers are added by the FastAPI middleware.
- The container runs as an unprivileged user and keeps application code read-only while allowing the data and required runtime folders to be writable.
- GitHub Actions runs unit tests, JavaScript syntax validation, pip-audit, and Bandit.

## Operational checks still required before production promotion

These depend on the hosting account and cannot be verified from repository code alone:

1. Confirm the production app's kept/persistent folder includes `/data`.
2. Confirm production `DATABASE_URL` points to the intended persistent PostgreSQL database and that backups are enabled.
3. Keep `API_KEY`, `CHAINLIT_AUTH_SECRET` (or `NIMI_GUEST_SECRET`), and optionally `NIMI_STORAGE_SECRET` in the hosting secret manager. Use unique random values of at least 32 characters for the signing secrets; never commit or paste them into issues or chat.
4. If OpenRouter is enabled, configure its key only in the hosting secret manager. The application is designed to request only `openrouter/free`.
5. Confirm the production app is configured for one instance unless attachment storage is moved to shared object storage. Local filesystem blobs are not a multi-replica shared-storage design.
6. Verify provider backup/restore procedures and the app's public URL/TLS configuration.
7. After any future deployment, smoke-test guest isolation in two separate browser profiles, chat history, memory, PDF/image uploads, and a full restart.

## Public guest-access trade-offs

Nimi currently permits access without account registration. A browser's signed guest cookie is its identity and is required to recover that browser's chats and memories. Clearing browser cookies or changing browsers creates a new guest identity; there is no account-based recovery. Anyone with access to an unlocked browser profile may be able to access that profile's Nimi history.

The current database-backed global rate limit is an application-level guard, not a substitute for provider-side quotas, edge/WAF protection, or abuse monitoring.

## Verification status

The new data-directory regression tests are included in this pull request. Automated results must be read from the GitHub Actions run for the pull request; no CI pass is asserted by this document. Blitz staging and production settings must be checked separately by the app owner.
