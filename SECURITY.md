# Nimi security and account setup

## Private access

Nimi uses individual usernames and password hashes. The application fails closed:
if `NIMI_USERS_JSON` is missing, malformed, or does not contain a valid user entry,
password authentication rejects the login.

Generate the account configuration on a trusted local computer:

```bash
python tools/create_users.py
```

Create one account for the owner and one for each invited friend (up to 20).
Use a unique password of at least 14 characters for every account. The script
prints a JSON object containing PBKDF2-SHA256 hashes, not plain-text passwords.

In Blitz, add an environment variable / secret named `NIMI_USERS_JSON` and paste
the generated JSON value. Do not commit the JSON, send it in chat, or put it in
a public issue. Share each username and password with its owner privately.

To revoke access, remove that username/hash pair from the secret and redeploy.
For a suspected password leak, remove the account and generate a new password hash.

## Required deployment settings

- Keep `features.mcp.enabled = false`.
- Set `NIMI_USERS_JSON` in the hosting provider's secret/environment settings.
- Set `DATABASE_URL` to a managed PostgreSQL database with TLS enabled. Do not use
  the local JSON memory fallback for a shared 20-person deployment.
- Keep `API_KEY` in the hosting provider's secret store only.
- Use HTTPS and restrict the allowed origin to the actual Nimi hostname.
- Back up the database securely and restrict database access to the application.

## Operational limits

Uploads are restricted to PDF, plain text, Markdown, CSV, PNG, JPEG and WebP;
maximum five files per message and 10 MB per file.

GitHub Actions runs `pip-audit` on pushes, pull requests and weekly. Review and
resolve any reported vulnerability before deploying.

## Important

This is a hardening baseline, not a guarantee of complete security. The hosting
provider's network controls, database TLS/access policy, authentication rate
limiting, backup security and runtime behavior must also be checked.
