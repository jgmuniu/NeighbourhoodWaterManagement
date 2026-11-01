# Phase 8 — Financial reports, statements and payment controls

## Added
- Household account statement PDF with bill totals, allocations, paid amounts and balances.
- Expanded Excel workbook with Financial Summary, Payments and Consumption sheets. Exports can be filtered by `YYYY-MM` or year.
- Administrator-only payment reversal. Reversal marks the original payment as reversed; it does not delete the payment. The affected bill balances and statuses are recalculated, and the reason is written to the audit trail.
- Timestamped backup command supporting SQLite copies and PostgreSQL custom-format dumps.
- Desktop Reports & Backup tab now exposes statements, filtered reports and payment reversal.

## Run a backup
From the desktop folder, with the project environment activated:

```powershell
python backup.py D:\NWM-Backups
```

On Ubuntu/Linux:

```bash
python backup.py /media/$USER/BackupDrive/NWM-Backups
```

For PostgreSQL, install the PostgreSQL client tools and ensure `pg_dump` is on PATH. The configured database URL is used by the backup script. Protect backup folders because they contain household and payment information. Keep at least one copy on a separate drive and periodically test restoration.

To schedule backups, configure Windows Task Scheduler or a Linux systemd timer to run the command above at a chosen interval. Scheduling is configured on the host machine; the app does not silently create operating-system scheduled tasks.

## Validation and accounting notes
- A reversal requires Administrator role and a non-empty reason.
- Reversed payment records remain in the database for traceability and are excluded from paid totals.
- For household-level payments, allocations are excluded when their parent payment is reversed.
- Excel reports include reversed payments, clearly marked, for audit transparency; balances exclude them.

## Known limitations
- This phase does not add automatic cloud backups or encryption-at-rest for exported files.
- Backup restore remains a deliberate operator/admin maintenance task. PostgreSQL restoration uses `pg_restore`; SQLite restoration uses the existing restore workflow.
- Reports are generated from the records currently stored. They do not independently verify meter readings or reconcile M-Pesa/bank statements.
- The desktop application still connects directly to the configured database; use a trusted LAN/VPN and firewall rules for shared PostgreSQL deployments.
- Full mobile sync replay and conflict resolution remain outstanding.
