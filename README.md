# Neighbourhood Water Management

A desktop-first household water submeter billing system for Windows and Ubuntu, with a FastAPI service and Flutter Android companion.

## Project structure

- `desktop/` — PySide6 desktop client and SQLAlchemy data services
- `backend/` — FastAPI service
- `mobile/` — Flutter Android client source
- `docs/` — phase notes and setup guidance
- `docker-compose.yml` — PostgreSQL + API shared deployment

## Run locally with SQLite

```bash
cd desktop
python -m venv venv
```

Activate the environment, then:

```bash
pip install -r requirements.txt
python main.py
```

The default database is stored in the user's application data directory.

## Run shared PostgreSQL + API

Copy `.env.example` to `.env`, change both secrets, then run:

```bash
docker compose up -d --build
```

See `docs/PHASE_7.md` for connecting desktop and Android clients, backups, security and current limitations.

## Currency and billing defaults

- Currency: KES
- Default payment due day: 10
- Water price: administrator-configurable
- Billing periods: custom monthly dates

This is a development project, not yet a production-certified financial system. Back up data, restrict network access and test all financial workflows before real billing.

## Phase 8 — Financial reports and payment controls

See [`docs/PHASE_8.md`](docs/PHASE_8.md) for household statement PDFs, expanded Excel reports, administrator payment reversals and scheduled-backup setup. Run a manual backup with `python desktop/backup.py <destination-folder>` from the desktop directory (or run `python backup.py <destination-folder>` while inside `desktop/`).


## Phase 9 — mobile synchronization
See [docs/PHASE_9.md](docs/PHASE_9.md) for offline queue replay, idempotent write endpoints, request monitoring, and recovery guidance.

## Phase 10 — Deployment foundation

Phase 10 adds Windows/Linux PyInstaller bundle scripts, an Android release APK script, API/database readiness monitoring, Docker health checks, and a release checklist. See `docs/PHASE_10.md` and `docs/RELEASE_CHECKLIST.md`. Native installers and signed release builds must be produced and tested on their target platforms.
