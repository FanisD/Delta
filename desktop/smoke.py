"""Headless sidecar smoke check used by release jobs and local verification."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
import os


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python desktop/smoke.py PATH_TO_SIDECAR", file=sys.stderr)
        return 2
    environment = os.environ.copy()
    environment.update({"APP_PORT": "18736", "APP_NO_BROWSER": "1"})
    process = subprocess.Popen([sys.argv[1]], env=environment)
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen("http://127.0.0.1:18736/api/health", timeout=1) as response:
                    if response.status == 200:
                        return 0
            except OSError:
                time.sleep(0.25)
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
