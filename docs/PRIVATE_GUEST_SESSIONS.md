# Private Guest Sessions

Nimi remains publicly accessible without registration. Each browser receives a random guest identity in a signed, HTTP-only cookie. The server validates that cookie before creating the Chainlit user session.

## Required environment variables

- `API_KEY`: Gemini API key used by Nimi.
- `CHAINLIT_AUTH_SECRET`: A strong random secret of at least 32 characters. Chainlit uses it to sign authentication tokens.
- `NIMI_GUEST_SECRET`: Recommended separate random secret of at least 32 characters for guest-cookie signatures. If omitted, Nimi derives a separate signing key from `CHAINLIT_AUTH_SECRET`.
- `DATABASE_URL`: Recommended PostgreSQL connection string for persistent chats and memories. If omitted, Nimi uses SQLite in `DATA_DIR/chat.db`.

Do not commit secrets to Git. Add them in the hosting provider's environment-variable settings.

## Storage requirements

- Keep the PostgreSQL database persistent when using `DATABASE_URL`.
- Without PostgreSQL, mount a persistent disk at `/data` so `/data/chat.db` survives container replacement.
- Do not run multiple replicas with SQLite on separate local disks. Use shared PostgreSQL for multi-replica deployments.

## Guest identity and recovery

The guest cookie is valid for one year and is marked Secure, HttpOnly, and SameSite=Lax. Its identity is stable for the same browser profile while the cookie remains available.

Clearing browser cookies, using a different browser profile, or switching devices creates a different guest identity. Without an optional recovery feature, the old guest's chats and memories cannot be linked to the new identity. Do not copy a guest cookie to another person: possession of the cookie grants access to that guest's history.

## User memory commands

- `/memory` lists saved facts for the current browser identity.
- `/forget-memory NUMBER` removes one item from that list (for example, `/forget-memory 2`).
- `/clear-memory` removes all saved facts for the current browser identity.
- `/export` exports the current chat's in-memory conversation history.

Removing a saved fact from Nimi memory does not erase the original message from the chat transcript. Delete the chat separately if you also want its conversation history removed.

## Before deploying

1. Configure the required secrets in the hosting provider.
2. Confirm PostgreSQL or persistent `/data` storage is configured.
3. Deploy this branch to a staging service, not the production service.
4. Test two independent browser profiles: each must see only its own new chats and memories.
5. Test refresh, browser restart, chat resume, and a deliberately modified guest cookie.
6. Confirm the app does not expose the login form and that invalid/missing secrets fail closed.

The guest identity is not a user account. It provides private browser-scoped history without requiring registration.
