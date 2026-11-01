from __future__ import annotations
import os
import sys
import urllib.error
import urllib.request

base = os.getenv('NWM_API_URL', 'http://127.0.0.1:8000').rstrip('/')
checks = [('/health', 'API liveness'), ('/health/ready', 'Database readiness')]
failed = False
for path, label in checks:
    try:
        with urllib.request.urlopen(base + path, timeout=5) as response:
            body = response.read().decode('utf-8', errors='replace')
            ok = response.status == 200
            print(f"{'PASS' if ok else 'FAIL'} {label}: HTTP {response.status} {body[:240]}")
            failed |= not ok
    except (OSError, urllib.error.URLError) as exc:
        print(f'FAIL {label}: {exc}')
        failed = True
sys.exit(1 if failed else 0)
