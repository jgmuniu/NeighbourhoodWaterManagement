#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/desktop"
python3 -m venv .build-venv
.build-venv/bin/python -m pip install --upgrade pip
.build-venv/bin/python -m pip install -r requirements.txt pyinstaller
.build-venv/bin/pyinstaller --noconfirm --clean --windowed --name NeighbourhoodWaterManagement main.py
OUT="$ROOT/release/linux"
mkdir -p "$OUT"
cp -a dist/NeighbourhoodWaterManagement "$OUT/"
cp "$ROOT/README.md" "$OUT/"
cat > "$OUT/NeighbourhoodWaterManagement.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Neighbourhood Water Management
Comment=Neighbourhood household water billing
Exec=$OUT/NeighbourhoodWaterManagement/NeighbourhoodWaterManagement
Terminal=false
Categories=Office;Finance;
DESKTOP
cat > "$OUT/INSTALL.txt" <<INSTALL
Run the application bundle executable: ./NeighbourhoodWaterManagement/NeighbourhoodWaterManagement
The bundle must remain in its folder. This is an unpacked Linux application bundle, not a DEB/RPM package.
INSTALL
printf 'Linux application bundle created at %s\n' "$OUT"
