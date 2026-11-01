$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Desktop = Join-Path $Root 'desktop'
Set-Location $Desktop
python -m venv .build-venv
& .\.build-venv\Scripts\python.exe -m pip install --upgrade pip
& .\.build-venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
& .\.build-venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name NeighbourhoodWaterManagement main.py
$Out = Join-Path $Root 'release\windows'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
Copy-Item -Recurse -Force (Join-Path $Desktop 'dist\NeighbourhoodWaterManagement') $Out
Copy-Item (Join-Path $Root 'README.md') $Out
Write-Host "Windows application bundle created at $Out"
Write-Host 'This is an unpacked PyInstaller bundle, not a signed MSI installer.'
