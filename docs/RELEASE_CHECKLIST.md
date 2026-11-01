# Release checklist

- [ ] Set unique PostgreSQL password and API secret in `.env`.
- [ ] Keep `.env`, signing keys, database files, and backups out of source control.
- [ ] Confirm `/health` and `/health/ready` both return HTTP 200.
- [ ] Create initial administrator and separate operator/viewer accounts.
- [ ] Confirm desktop and API use the same intended database URL.
- [ ] Test bill generation, arrears, payment allocations, reversals and audit records.
- [ ] Test offline queue, retry with the same idempotency key, and review-required cases.
- [ ] Run a backup and restore it into a separate test database.
- [ ] Build Windows bundle on Windows.
- [ ] Build Linux bundle on the target Linux distribution/architecture.
- [ ] Build and test Android APK on a physical device.
- [ ] Use HTTPS for production API access and disable cleartext HTTP in production Android builds.
- [ ] Configure firewall, database access restrictions, monitoring and backup retention.
- [ ] Obtain administrator acceptance before importing live household/accounting data.
