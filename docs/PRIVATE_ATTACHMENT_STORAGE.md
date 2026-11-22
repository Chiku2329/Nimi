# Private attachment storage

Nimi stores Chainlit attachment bytes under `NIMI_STORAGE_DIR`, which defaults
to `$DATA_DIR/elements` (normally `/data/elements` on Blitz). The directory
is not mounted as public static content.

The SQLAlchemy data layer stores attachment metadata and object keys in the
existing PostgreSQL database. When a guest opens their own conversation
history, Chainlit asks the storage provider for a fresh, short-lived HMAC-signed
read URL. FastAPI serves the file only after validating that signature and
expiry. Object keys are path-validated and cannot escape the storage root.

The signing key is derived separately from `NIMI_STORAGE_SECRET`,
`NIMI_GUEST_SECRET`, or `CHAINLIT_AUTH_SECRET`. No new secret is required if
Nimi's existing guest/auth secret is already configured. A dedicated
`NIMI_STORAGE_SECRET` may be set to rotate storage URL signing independently.

## Operational requirements

- Keep `DATA_DIR` on Blitz's persistent app storage volume.
- Do not expose `/data/elements` as a static/public directory.
- Do not delete or reset the existing PostgreSQL database or `/data`.
- Existing attachments uploaded before this provider was enabled cannot be
  recovered from the data layer; users need to upload them again if needed.
- The app's existing upload validation limits remain in force.
- Signed URLs expire after Chainlit's `STORAGE_EXPIRY_TIME` (one hour by
  default). Reopening a thread generates fresh URLs.
