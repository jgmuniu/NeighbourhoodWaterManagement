# Phase 2 additions

This milestone adds:
- Custom billing period records with start, end and due dates
- Validation against overlapping periods
- Audit log storage and audit viewer
- PDF bill export
- Excel bill export
- Database backup with SQLite WAL checkpoint
- Backup integrity verification and safe restore with pre-restore copy

Important limitations:
- Existing bills created in phase 1 are not automatically assigned custom due dates.
- The bill generation UI still needs to be connected to a selected custom period and should be upgraded before live use.
- Role-based authentication, payment allocation ledger, meter replacement workflow, mobile app and synchronization remain future milestones.
- Audit helper is available; every existing mutation path still needs to be wired through it before claiming a complete audit trail.
