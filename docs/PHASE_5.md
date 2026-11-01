# Phase 5 — FastAPI backend foundation

## Delivered
- FastAPI application with `/health` and OpenAPI documentation.
- HMAC-SHA256 bearer tokens with configurable expiry.
- Authentication against the same PBKDF2 password hashes used by the desktop app.
- Role checks for write operations (Administrator and Operator); Viewer can read.
- Household, meter, billing-period, reading, bill, household-account and payment endpoints.
- Cursor-based audit change feed for synchronization polling.
- Validated change-envelope acknowledgement endpoint; no untrusted client payload is applied directly to financial records.
- CORS allowlist configuration and Windows/Linux setup instructions.

## Important architecture boundary
The default database is the same local SQLite database configured by the desktop app. This is suitable for a single host running desktop and API together. It is not a safe multi-computer shared database over a network folder. Multi-device neighbourhood deployment requires PostgreSQL, migrations, TLS, device identity, offline queue persistence, idempotent mutation keys, conflict policies and tested sync replay.

## Verification
Python source files are syntax-checked during packaging. Full API runtime tests require installing `backend/requirements.txt` and running the service in a configured environment.
