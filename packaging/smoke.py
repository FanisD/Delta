from __future__ import annotations

import subprocess
import sys
import time
import os
from pathlib import Path
from urllib.request import urlopen


def main() -> None:
    executable = Path(sys.argv[1])
    if not executable.is_file():
        raise FileNotFoundError(executable)
    environment = os.environ.copy()
    environment["APP_PORT"] = "49152"
    environment["APP_DATA_DIR"] = str(executable.parent / "smoke-data")
    process = subprocess.Popen(
        [str(executable)], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        for _ in range(300):
            try:
                with urlopen("http://127.0.0.1:49152/api/health", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("Packaged Delta launcher did not answer /api/health.")
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()
