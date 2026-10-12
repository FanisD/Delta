# Desktop shell decision

Delta uses Tauri 2 rather than Electron. Electron has mature sidecar and
webview behavior but adds a bundled Chromium runtime and typically 100–150 MB
per install. Tauri adds only a small Rust shell and uses WebView2, WKWebView,
or WebKitGTK already supplied by the OS, which is a better fit because Delta
already ships the Python backend. The trade-off is OS webview-version
fragmentation and a smaller sidecar ecosystem; the health-polling manager and
launcher fallback address those risks.

The native window loads the live loopback URL served by the existing
PyInstaller backend. No presentation, API, or persistence business logic is
implemented in Rust.
