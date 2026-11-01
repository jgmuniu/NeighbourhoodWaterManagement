#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/mobile"
command -v flutter >/dev/null || { echo 'Flutter SDK is required.' >&2; exit 1; }
flutter pub get
flutter analyze
flutter test
flutter build apk --release
mkdir -p "$ROOT/release/android"
cp build/app/outputs/flutter-apk/app-release.apk "$ROOT/release/android/NeighbourhoodWaterManagement.apk"
printf 'APK copied to %s\n' "$ROOT/release/android/NeighbourhoodWaterManagement.apk"
