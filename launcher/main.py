from __future__ import annotations

import socket
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def main() -> None:
    backend_directory = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_directory))

    import uvicorn
    from app.main import app

    port = int(os.environ.get("APP_PORT", free_port()))
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("Delta server did not start within 30 seconds.")
    webbrowser.open(f"http://127.0.0.1:{port}/")
    try:
        thread.join()
    except KeyboardInterrupt:
        server.should_exit = True


if __name__ == "__main__":
    main()
