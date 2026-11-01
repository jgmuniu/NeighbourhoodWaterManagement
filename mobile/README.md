# Phase 6 — Android mobile application

Flutter Android companion for Neighbourhood Water Management. This phase adds the app source, local SQLite cache/outbox, API login, household and bill views, reading/payment forms, and configurable API address.

## Requirements

- Flutter stable (Dart 3.3 or newer)
- Android Studio with Android SDK and an Android device/emulator
- Phase 5 FastAPI backend running and reachable from the phone

## Generate Android build scaffolding

From this `mobile` directory, run:

```bash
flutter create --platforms=android --org ke.co.nwm .
```

This generates the Gradle wrapper and Android project scaffolding for the installed Flutter version. Keep the app source under `lib/` and ensure the generated Android manifest includes Internet permission. The supplied `android/app/src/main/AndroidManifest.xml` already includes it and allows cleartext HTTP for local development only.

Then run:

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

To build an APK:

```bash
flutter build apk --release
```

The APK will be written to `build/app/outputs/flutter-apk/app-release.apk`.

## Connecting to the backend

- Android emulator: `http://10.0.2.2:8000` reaches the host computer's localhost.
- Physical phone: use the computer's LAN IPv4 address, for example `http://192.168.1.20:8000`, and ensure the phone and computer are on the same Wi-Fi network.
- Internet: use a deployed HTTPS API hostname. Do not expose the development server directly to the public internet.

The default address is `http://10.0.2.2:8000`. Change it in Settings on the app. Sign in using a user account created in the desktop application.

## Offline behavior and limitations

- Household, meter, bill and billing-period lists are cached locally in SQLite after a successful server refresh.
- The app can display cached lists when the API cannot be reached.
- Meter reading and payment submissions that fail are stored in a local outbox for later review.
- **Automatic outbox replay is intentionally not enabled yet.** The Phase 5 `/sync/push` endpoint only acknowledges change envelopes and does not commit financial changes. Pending entries must not be marked as synchronized until submitted through their validated API endpoints. This avoids silently overwriting accounting records.
- This phase does not yet implement push notifications, full account-statement pagination, receipt PDF generation, device registration, conflict resolution, or production-grade HTTPS certificate handling.

## Security notes

The Android manifest permits cleartext traffic to support local development over Wi-Fi. Production deployments must use HTTPS and disable cleartext traffic. Tokens are currently stored in the local settings database; production release should replace this with Android Keystore-backed secure storage and add token revocation/device management.
