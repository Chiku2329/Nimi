# Chainlit storage warning

Nimi currently uses PostgreSQL through Chainlit's `SQLAlchemyDataLayer` for
chat users, threads, messages, and steps. The data layer is intentionally
created without a blob-storage provider because no persistent object-storage
service is configured for this app.

Chainlit's warning:

```
SQLAlchemyDataLayer storage client is not initialized and elements will not be persisted!
```

is therefore expected. It does **not** mean PostgreSQL chat-message history
is disabled. It does mean Chainlit file elements (for example, uploaded files
or generated downloadable elements) are not durably stored by the data layer.

Nimi reads supported uploads during the active message and passes extracted
text or image data to the model. That request-time processing is separate from
retaining the original attachment for later reopening from chat history.

Do not silence this warning or point file storage at an unverified directory.
Durable attachment history requires a configured, access-controlled blob
storage provider (or a separately reviewed persistent local-storage adapter).
Any future provider must preserve guest isolation, enforce safe object keys,
and serve reads only to the owning guest. Configure and test that provider
before claiming that attachments survive refreshes.

The current deployment's PostgreSQL and `/data` contents must not be reset or
migrated as part of this work.
