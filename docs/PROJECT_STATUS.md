# Project status — Phase 8

## Implemented
- Aqua-themed PySide6 desktop application with SQLite or configured PostgreSQL connection
- Household, meter, meter replacement, reading, water price and custom billing-period management
- Bill generation, arrears carry-forward, payment recording and household payment allocations
- Authentication with Administrator, Operator and Viewer roles
- Audit trail for key financial and administrative actions
- FastAPI backend foundation and Flutter mobile source with local cache/outbox foundation
- PDF bill export and all-bills Excel export
- Phase 8 household account statement PDF
- Phase 8 Excel workbook with financial summary, payment ledger and meter reconciliation/consumption sheet; optional monthly or annual filter
- Administrator-only payment reversal, retained as a reversed transaction with mandatory reason and audit record
- Timestamped SQLite and PostgreSQL backup command (`desktop/backup.py`)

## Still outstanding / not fully verified
- Mobile outbox replay, idempotent write processing and conflict-safe bidirectional synchronization
- End-to-end deployment test of Docker Compose and PostgreSQL on a separate host
- Flutter Android build/APK verification and Windows/Linux desktop installers
- Automated backup scheduling must be configured in Windows Task Scheduler or a Linux systemd timer
- Exported files are not encrypted by the application; protect destination folders and drives
- Comprehensive production acceptance testing with real neighbourhood records


## Phase 9
- Idempotent API endpoints for offline readings and payments.
- Android persistent outbox replay, device ID, pull cursor, and review-required state.
- Server request status and diagnostics endpoints.
- See `PHASE_9.md` for the recovery caveat and remaining sync limitations.
