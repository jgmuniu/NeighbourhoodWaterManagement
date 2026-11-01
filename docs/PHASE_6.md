# Phase 6 — Flutter Android client

Added a Flutter mobile application source under `mobile/` with aqua Material 3 styling, API login, configurable backend URL, cached household/meter/bill/period lists, household account lookup, reading and payment forms, and a SQLite outbox for submissions that fail while offline.

## Important scope boundary

This phase is a mobile source-code foundation, not a signed/installable APK. Flutter/Android SDK was not available in the build environment, so `flutter pub get`, analyzer, widget tests and APK compilation have not been run. Generate Android Gradle scaffolding from `mobile/` using `flutter create --platforms=android --org ke.co.nwm .`, then run `flutter pub get`, `flutter analyze`, `flutter test` and `flutter build apk --release`.

Offline lists can be viewed from cache. Failed reading/payment submissions are stored in a local outbox. Automatic replay is deliberately disabled because Phase 5's sync push endpoint does not commit those changes; submitting financial data without a safe idempotency/conflict protocol could create duplicates. Production should use HTTPS, secure token storage backed by Android Keystore, server-side device registration and audited conflict resolution.
