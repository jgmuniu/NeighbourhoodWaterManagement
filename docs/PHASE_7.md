# Phase 7 — Shared database and client integration foundation

## What changed

- Desktop and API now read `NWM_DATABASE_URL` from the environment. If it is not set, desktop continues using its local SQLite database.
- Added PostgreSQL 16 and a persistent Docker Compose volume.
- Added a backend container image and PostgreSQL driver (`psycopg`).
- Added a shared-database deployment path so desktop installations and the API can use the same PostgreSQL database.
- Mobile can point at the same API using its Connection settings. Use the computer/server LAN address for Wi-Fi access.
- SQLite file backup/restore actions now explicitly refuse to run against PostgreSQL; use PostgreSQL-native backups instead.

## Start the shared backend

1. Install Docker Desktop (Windows) or Docker Engine + Compose (Ubuntu).
2. Copy `.env.example` to `.env` in the project root.
3. Replace both passwords/secrets with long, unique values. Do not commit `.env` or share it.
4. Start services:

```bash
docker compose up -d --build
```

5. Check the API at `http://localhost:8000/health` and documentation at `http://localhost:8000/docs`.

The database is persistent in the `nwm_postgres_data` Docker volume.

## Connect desktop clients

Install desktop dependencies, including the PostgreSQL driver:

```bash
cd desktop
python -m pip install -r requirements.txt
```

Set `NWM_DB_BIND_ADDRESS` in the server `.env` to the server LAN interface address (not `0.0.0.0`) if desktop clients on other computers must reach PostgreSQL. Restrict TCP 5432 in the host firewall to trusted neighbourhood devices. Then set the same database URL used by the API, replacing `SERVER_IP` with the server LAN address.

PowerShell:

```powershell
$env:NWM_DATABASE_URL = "postgresql+psycopg://nwm_user:YOUR_PASSWORD@SERVER_IP:5432/nwm_db"
python main.py
```

Ubuntu:

```bash
export NWM_DATABASE_URL='postgresql+psycopg://nwm_user:YOUR_PASSWORD@SERVER_IP:5432/nwm_db'
python main.py
```

Keep PostgreSQL bound to `127.0.0.1` unless LAN desktop connections are required. Do not expose PostgreSQL port 5432 to the public internet. In a LAN installation, allow it only from trusted client devices. For remote access, use a VPN or secured network tunnel and HTTPS for the API.

## Connect Android

Set the mobile app API address to `http://SERVER_IP:8000` when on the same trusted Wi-Fi network. For internet use, deploy the API behind HTTPS and configure the public HTTPS URL. Do not expose a plain HTTP API directly to the internet.

## Backup and restore

SQLite backup/restore remains available in local SQLite mode. For the shared PostgreSQL database, create a backup:

```bash
docker compose exec -T database pg_dump -U nwm_user -d nwm_db -Fc > nwm_backup.dump
```

Restore into a stopped/maintenance database after making a second backup:

```bash
docker compose exec -T database pg_restore -U nwm_user -d nwm_db --clean --if-exists < nwm_backup.dump
```

Review the target database carefully before using `--clean`; it replaces existing objects.

## Current limitations

- This phase establishes shared PostgreSQL connectivity; it does not automatically migrate existing SQLite data. A separately tested export/import migration is required before switching a live neighbourhood to PostgreSQL.
- The desktop and API can share one PostgreSQL database when configured with the same URL. Local SQLite installations remain independent until migrated.
- Mobile cached lists can be viewed offline, but queued offline writes are not automatically replayed. The `/sync/push` endpoint is an acknowledgement/diagnostic endpoint, not a write replication protocol.
- The audit cursor feed is not a complete conflict-safe synchronization engine. Device identity, idempotency keys, conflict policies, deletion tombstones and retry reconciliation remain future work.
- The desktop currently uses direct SQLAlchemy access, not API-mediated access. For remote deployments, VPN/firewall restrictions are essential; a later desktop API client should replace direct database access.
- Flutter/Android compilation and Windows/Linux installer packaging have not been verified in this environment.

## Verification

Run Python syntax checks with:

```bash
python - <<'PY'
import ast
from pathlib import Path
for path in [*Path('desktop').glob('*.py'), *Path('backend').rglob('*.py')]:
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
print('Python syntax OK')
PY
```

For a real deployment, additionally test login, household creation, reading submission, bill/account queries and payment recording from both desktop and Android clients against the same test PostgreSQL database before importing production records.
