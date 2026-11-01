# Phase 5 — FastAPI service

This phase adds an authenticated HTTP API over the existing SQLAlchemy database. The service uses the same SQLite database as the desktop app by default, so a single computer can run both. For multiple computers, do not place SQLite on a shared network drive: deploy PostgreSQL and configure the database URL for all clients in a later deployment step.

## Setup (Windows PowerShell)

```powershell
cd backend
py -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:NWM_API_SECRET = "replace-this-with-a-long-random-secret"
$env:NWM_CORS_ORIGINS = "http://localhost,http://127.0.0.1"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Setup (Ubuntu/Linux)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export NWM_API_SECRET="replace-this-with-a-long-random-secret"
export NWM_CORS_ORIGINS="http://localhost,http://127.0.0.1"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation and `http://127.0.0.1:8000/health` for a health check.

## Authentication

1. Create the first Administrator through the desktop application's first-run setup.
2. Start the API with `NWM_API_SECRET` set to a long, random value. Never use the example value in a real deployment.
3. Call `POST /auth/login` with the desktop-created username and password.
4. Send `Authorization: Bearer <access_token>` on protected requests.

Tokens are HMAC-SHA256 signed and expire after `NWM_TOKEN_MINUTES` (default 12 hours). Password verification reuses the desktop application's PBKDF2 password storage. Never expose the API directly to the public internet without HTTPS, firewall rules, secret management, rate limiting and a production deployment review.

## Endpoints

- `GET /health`
- `POST /auth/login`, `GET /auth/me`
- `GET/POST /households`
- `GET /meters`
- `GET /billing-periods`
- `GET/POST /readings`
- `GET /bills`
- `GET /households/{id}/account`
- `POST /payments`
- `GET /sync/pull?after_id=0`
- `POST /sync/push`

Read operations require an authenticated user. Creating households, readings and payments requires Administrator or Operator. The sync pull endpoint is an audit-backed change feed; clients then retrieve canonical data from the resource endpoints. Push currently validates and acknowledges change envelopes only; it does not silently overwrite financial records. Full offline queue replay, conflict resolution, device registration and automatic two-way synchronization are future work.

## Database

By default, the API imports the desktop configuration and uses the same local SQLite file. For multi-device use, a PostgreSQL database and coordinated migration are required. Do not use a shared SQLite file over Wi-Fi/NFS/SMB.
