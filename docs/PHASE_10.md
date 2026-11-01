# Phase 10 — Production readiness and deployment foundation

## Delivered in this phase

- Windows PyInstaller bundle build script: `scripts/build_windows.ps1`.
- Ubuntu/Linux PyInstaller bundle build script: `scripts/build_linux.sh`.
- Android release APK build script: `scripts/build_android.sh` (requires Flutter and Android SDK).
- Deployment probe: `scripts/check_deployment.py` checks API liveness and database readiness without printing credentials.
- API database readiness endpoint: `GET /health/ready` executes a database connectivity probe and returns HTTP 503 when the database cannot be reached.
- Docker Compose API health check.
- CORS allows the synchronization headers `X-Idempotency-Key` and `X-Device-Id` used by the mobile outbox.
- Existing desktop first-run administrator dialog remains the initial account setup flow.

## Windows desktop bundle

Run PowerShell from the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_windows.ps1
```

Output: `release/windows/NeighbourhoodWaterManagement/`. The output is an unpacked PyInstaller application bundle, not a signed MSI installer. Build it on Windows for Windows; do not cross-build from Linux.

## Ubuntu/Linux desktop bundle

```bash
chmod +x scripts/build_linux.sh
./scripts/build_linux.sh
```

Output: `release/linux/`. Build on the target Linux family/architecture. PyInstaller bundles are generally not portable across unrelated Linux distributions or CPU architectures. The generated `.desktop` file is a launcher template; review its absolute executable path after moving the bundle.

## Android release APK

Install Flutter stable and Android SDK/command-line tools, ensure `flutter doctor` reports the Android toolchain ready, then run:

```bash
./scripts/build_android.sh
```

Output: `release/android/NeighbourhoodWaterManagement.apk`. The build script runs dependency resolution, static analysis and Flutter tests before creating the release APK. A signed Play Store release still requires a private signing key and Gradle signing configuration; do not commit signing credentials.

## Server deployment

1. Copy `.env.example` to `.env`.
2. Replace `POSTGRES_PASSWORD` and `NWM_API_SECRET` with long, unique random values. Generate a secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Keep `.env` private and out of version control.
3. Review `NWM_DB_BIND_ADDRESS`; keep PostgreSQL bound to `127.0.0.1` unless there is a documented secured network requirement.
4. Start the services:

```bash
docker compose up -d --build
```

5. Check status:

```bash
docker compose ps
python scripts/check_deployment.py
```

The API liveness endpoint is `/health`; `/health/ready` additionally checks the configured database. The readiness endpoint is diagnostic, not an authenticated administration interface.

## First administrator and security

Create the first administrator through the desktop application's first-run setup dialog, then use the same database configuration for the API and desktop. Use a unique password and create separate accounts for operators/viewers. Do not expose PostgreSQL directly to the public internet. For remote access, deploy behind HTTPS with a reverse proxy or trusted VPN, restrict firewall rules, and use a trusted TLS certificate.

## Release verification status

The scripts and configuration are source deliverables. Native builds are environment-specific and must be run on their respective operating systems. This development environment does not certify a Windows executable, Linux package, signed Android APK, Docker production deployment, or security audit. The Linux/Windows scripts create unpacked PyInstaller bundles, not native MSI/DEB/RPM installers.

Before live billing, test on a staging database with representative households, meter readings, partial payments, reversals, offline submissions, duplicate retries, restore-from-backup, and role permissions. Keep verified backups outside the server's primary disk.
