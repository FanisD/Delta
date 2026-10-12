# Delta desktop app

Delta's desktop track is a Tauri 2 shell around the same PyInstaller backend
and `frontend/dist` used by the launcher. The shell chooses a free loopback
port, starts `delta-backend` from `desktop/binaries/`, waits for
`/api/health`, then navigates the native webview to that live URL. It does not
duplicate business logic.

## Local development

Install Rust and Tauri prerequisites, place a platform-built backend binary at
`desktop/binaries/delta-backend-<target-triple>` (Tauri resolves the target
suffix), then run `cargo tauri dev --manifest-path desktop/Cargo.toml`.
The normal launcher remains the fallback when native webview dependencies are
not available.

## Updates and signing

The updater configuration intentionally contains no key. Generate a keypair
with `cargo tauri signer generate`, store the private key only in the
`TAURI_SIGNING_PRIVATE_KEY` GitHub Actions secret, and put the public key in
`desktop/tauri.conf.json`. CI must publish a signed `latest.json` alongside
release artifacts. Code-signing certificates and notarization credentials are
also CI secrets; unsigned builds are expected to show platform warnings.

## Troubleshooting

- Linux: install `libwebkit2gtk-4.1-dev`, `libgtk-3-dev`, `libayatana-appindicator3-dev`,
  and `librsvg2-dev` (or the equivalent packages for the distribution).
- Older Windows: install the evergreen Microsoft Edge WebView2 runtime.
- macOS: Control-click an unsigned app and choose Open; notarized releases will
  not require this bypass.
- If the sidecar is missing, copy the matching PyInstaller binary into the
  target-triple filename under `desktop/binaries/`. The shell emits
  `delta://startup-failed` and keeps the loading window open rather than
  silently opening a blank page.

Both launcher and desktop artifacts receive every release. The launcher is the
maintenance-safe fallback and remains supported if a platform webview cannot
be installed.
