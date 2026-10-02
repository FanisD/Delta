from __future__ import annotations

import argparse
import logging
import os
import signal
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from filelock import FileLock, Timeout
from platformdirs import user_data_dir

VERSION = "0.1.0"


def free_port(preferred: int | None = None) -> int:
    if preferred:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", preferred))
                return preferred
            except OSError:
                pass
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Delta local presentation builder")
    parser.add_argument("--port", type=int, help="Port to listen on (falls back if busy)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser tab")
    args = parser.parse_args()
    data_dir = Path(os.environ.get("APP_DATA_DIR", user_data_dir("Delta", "FanisD")))
    data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=data_dir / "delta.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    lock = FileLock(str(data_dir / "launcher.lock"))
    try:
        lock.acquire(timeout=0)
    except Timeout:
        existing = _read_port(data_dir / "port")
        if existing:
            webbrowser.open(f"http://127.0.0.1:{existing}/")
            return
        raise RuntimeError("Delta is already running but its port could not be found.")

    backend_directory = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_directory))
    import uvicorn
    from app.main import app

    port = free_port(args.port or int(os.environ.get("APP_PORT", "0") or 0))
    (data_dir / "port").write_text(str(port), encoding="utf-8")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        lock.release()
        raise RuntimeError("Delta server did not start within 30 seconds.")
    logging.info("Delta %s started on port %s", VERSION, port)
    if not args.no_browser:
        webbrowser.open(f"http://127.0.0.1:{port}/")
    try:
        thread.join()
    except KeyboardInterrupt:
        server.should_exit = True
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        (data_dir / "port").unlink(missing_ok=True)
        lock.release()


def _read_port(path: Path) -> int | None:
    try:
        port = int(path.read_text(encoding="utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as response:
            return port if response.status == 200 else None
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    main()
