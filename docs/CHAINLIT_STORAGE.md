# Chainlit storage

Nimi uses PostgreSQL through Chainlit's `SQLAlchemyDataLayer` for users,
threads, messages, steps, and attachment metadata.

Attachment bytes are stored by Nimi's `PrivateLocalStorageClient` under
`NIMI_STORAGE_DIR`, defaulting to `$DATA_DIR/elements` (normally
`/data/elements` on Blitz). This provider is passed to
`SQLAlchemyDataLayer(storage_provider=...)`, so the
`SQLAlchemyDataLayer storage client is not initialized` warning should no
longer appear after the new version is deployed.

The storage directory is not exposed as public static content. The provider
returns short-lived HMAC-signed URLs; FastAPI validates each URL before
serving a file. Object keys are path-validated, and uploads continue to pass
through Nimi's existing file validation and size limits.

## Operational requirements

- Keep `DATA_DIR` on Blitz's persistent app storage volume.
- Do not mount `NIMI_STORAGE_DIR` as public/static content.
- Signing uses `NIMI_STORAGE_SECRET`, falling back to the existing
  `NIMI_GUEST_SECRET` or `CHAINLIT_AUTH_SECRET`; no additional secret is
  required if either existing secret is configured.
- Signed URLs expire after `STORAGE_EXPIRY_TIME` (one hour by default).
  Opening a thread again generates fresh URLs.
- Existing PostgreSQL data and `/data` must not be reset or migrated.
- Attachments uploaded before this provider was enabled were not retained by
  the old data layer and cannot be restored retroactively.
