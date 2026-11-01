# Phase 4 — Authentication, roles and household ledger

## Added
- First-run setup creates the initial administrator account; there is no hard-coded default password.
- Passwords are stored as PBKDF2-HMAC-SHA256 hashes with per-user random salts.
- Login checks account activation and records successful logins in the audit trail.
- User roles: Administrator, Operator and Viewer.
- Administrator-only user creation from the desktop interface.
- Service functions for password changes and account activation/deactivation; the last active administrator cannot be disabled.
- Household-level payments can be allocated oldest-outstanding-bill-first across multiple bills.
- Payment allocations are stored separately, preserving one payment receipt/reference while supporting multiple bill allocations.
- Household account summary reports billed, paid and outstanding amounts by bill.

## Role access in the desktop interface
- Administrator: all tabs and user administration.
- Operator: operational household, meter, reading, billing, payment and billing-period tabs; configuration, reconciliation, backup/restore and audit tabs are restricted.
- Viewer: household tab is available in read-only mode; other operational tabs are disabled.

## Run
From the `desktop` directory:

```powershell
python -m pip install -r requirements.txt
python main.py
```

On first launch, create an administrator username and password of at least 10 characters. Later launches require sign-in.

## Validation performed
- Python AST syntax validation passed for all Python source files.
- SQLite in-memory integration test passed for user creation, successful/failed authentication, oldest-first allocation of one household payment across two bills, and outstanding-balance calculation.

## Important limitations
- This is still a development build, not a production-secured financial system.
- Role restrictions are currently enforced at the desktop tab level; service-level authorization and a hardened API authorization layer are still required before multi-user/network deployment.
- Password reset and account deactivation service functions exist, but a complete user-management screen for those actions remains future work.
- The household account service returns account statements, but a dedicated printable statement and receipt UI is not yet included.
- Mobile, backend synchronization, automated installers and full regression testing remain future milestones.
