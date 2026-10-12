# Gamma-Style AI Presentation Builder: Build Plan

**Stack:** FastAPI (Python) backend + React (TypeScript) frontend
**Runs:** locally, with either cloud model API keys (Gemini, Claude, Grok, ...) or local models (Ollama, ...)
**Distribution:** downloadable per-OS builds from GitHub Releases and a website, in **two permanent forms**: a lightweight **launcher** (double-click, opens in the browser — ships first, Phase 8) and an installed **desktop app** (native window, Phase 9, added once the launcher is stable). Both wrap the exact same backend and frontend code.

---

## 1. Goal and scope

Build a local-first app where a user describes a topic (or pastes text, or imports a file/URL) and gets an editable, good-looking, card-based presentation. The user brings their own model: a cloud API key or a local Ollama model.

**MVP scope:** presentations only (documents and webpages come later).
**Non-goals:** real-time collaboration, hosting, billing, user accounts.

> Note: clone the *functionality*, not the identity. Do not reuse Gamma's name, logo, templates, copy or assets.

---

## 2. How it works (architecture in brief)

The LLM does **not** design slides. It writes a **structured document (JSON)**. A deterministic renderer plus a design system turns that JSON into visuals. That split is what makes every model swappable.

```
Input -> Outline -> Card content (JSON) -> Layout -> Theme -> Images/Charts -> Editor -> Export
```

| Step | What happens |
|---|---|
| Input | Prompt, pasted text, imported file/URL, or template, plus settings (card count, tone, language, audience) |
| Outline | LLM call 1 returns card titles and one-line summaries; the user edits before continuing |
| Card content | One LLM call per card fills a schema: layout hint plus blocks (heading, bullets, columns, quote, stat, table, image prompt, chart data) |
| Layout | Layout is a property of the card, chosen from a small library; cards grow to fit their content |
| Theme | Colors, fonts, spacing are design tokens (CSS variables), separate from content |
| Images / charts | LLM writes image prompts; images are generated async and slotted in; charts render from JSON data |
| Editor | Block editor over the document tree; AI edits are scoped LLM calls on a selection or card; a chat agent applies edit operations to the tree |
| Export | Web view is the native format; PDF/PNG via headless browser; PPTX by mapping the tree to PowerPoint shapes |

### Key architectural decisions for FastAPI + React

1. **Pydantic is the single source of truth for the schema.** FastAPI exports OpenAPI, and the frontend TypeScript types are generated from it (`openapi-typescript` or `@hey-api/openapi-ts`). Never hand-write the same type twice.
2. **Layouts are data, not just React components.** Define each layout as a spec (regions and block slots) so both the React renderer and the `python-pptx` exporter read the same source.
3. **PDF/PNG export renders the React app.** The backend opens a `/print/:deckId` route in headless Chromium (Playwright). The Chromium comes from the user's installed Chrome/Edge when available; otherwise Playwright downloads its own Chromium into the app-data folder on first export, which keeps the installer small.
4. **Generation streams over SSE** (Server-Sent Events), so cards appear as they are generated.
5. **One LLM gateway module** (LiteLLM) so no other code knows which provider is in use.
6. **Two run modes, one codebase.** Dev mode: Vite dev server proxying `/api` to FastAPI. Production mode (the shipped launcher): FastAPI serves the built React files itself, so the user runs a single process.
7. **All user data lives in the OS app-data folder** (via `platformdirs`), never next to the executable or in the repo: database, generated images, logs, downloaded browser. Upgrading or reinstalling the app never touches it. Dev mode can override the location with an env var.
8. **Local-only server.** Bind to `127.0.0.1` on a free port (fall back if the default is taken) and reject requests with unexpected `Host`/`Origin` headers, so other websites cannot talk to the local API.
9. **API keys go in the OS keyring** (Windows Credential Manager, macOS Keychain, Linux Secret Service) via `keyring`, with an encrypted-file fallback when no keyring is available.
10. **Build per OS on CI.** PyInstaller cannot cross-compile, so GitHub Actions builds on Windows, macOS and Linux runners.
11. **The desktop app is the launcher in a native window, not a rewrite.** It starts the same PyInstaller backend as a background process (a "sidecar") and points a native window at `http://127.0.0.1:<port>` instead of opening the system browser. No backend or frontend business logic changes for the desktop app; only the host shell differs.

---

## 3. Tech stack

### Backend

| Concern | Tool | Notes |
|---|---|---|
| Runtime / packaging | Python 3.12, **uv** | Fast dependency and venv management |
| Web framework | **FastAPI**, Uvicorn | Async throughout |
| Validation / schema | **Pydantic v2**, pydantic-settings | Discriminated unions for blocks |
| LLM gateway | **LiteLLM** | One interface for Gemini, Anthropic, xAI, OpenAI-compatible, Ollama |
| Structured output | **Instructor** (or LiteLLM `response_format` JSON schema) | Ollama supports JSON-schema constrained output via its `format` field |
| Local models | **Ollama** | Try 7-14B instruct models (Qwen, Llama, Gemma families) depending on your hardware |
| Database | **SQLite** via SQLAlchemy 2 + **Alembic**, aiosqlite | Deck stored as a JSON column plus metadata |
| Streaming | SSE (`sse-starlette` or `StreamingResponse`) | |
| Background work | `asyncio` tasks (in-process) | Skip Celery/Redis for local-first; revisit only if needed |
| Secrets | **keyring** (+ `cryptography` Fernet file as fallback) | API keys in the OS keyring, never returned to the frontend |
| App paths | **platformdirs** | OS-correct data, config and log folders |
| Launcher / packaging | **PyInstaller** (`--onedir`), stdlib `webbrowser` | Starts the server, opens the browser, bundles Python + built frontend + prompts + migrations |
| Desktop shell (Phase 9) | **Tauri** (Rust) | Native window wrapping the same backend as a sidecar process; far smaller than Electron since it uses the OS's built-in webview instead of bundling Chromium |
| Prompts | **Jinja2** templates in `backend/app/prompts/` | Versioned, testable |
| Image providers | Gemini/OpenAI image APIs, ComfyUI or Automatic1111 (local), Unsplash/Pexels (stock) | Behind one provider interface |
| Export | **Playwright for Python** (PDF/PNG), **python-pptx** (PPTX) | |
| Import | PyMuPDF or pdfplumber (PDF), python-docx (DOCX), trafilatura (URLs) | |
| Quality | pytest, pytest-asyncio, httpx, respx, **Ruff**, mypy or pyright | |

### Frontend

| Concern | Tool | Notes |
|---|---|---|
| Build | **React + Vite + TypeScript** | |
| Routing | React Router | |
| Styling | **Tailwind CSS**, **shadcn/ui**, CSS variables for themes | |
| Server state | **TanStack Query** | |
| UI state | **Zustand** (+ Immer for undo/redo patches) | |
| Rich text editor | **TipTap** (ProseMirror) | BlockNote is a faster start; Lexical is another option |
| Drag and drop | dnd-kit | Card reordering |
| Charts / diagrams | Recharts (or ECharts), Mermaid | |
| Icons | Lucide | |
| API client | Generated from OpenAPI | |
| Quality | Vitest, React Testing Library, Playwright (e2e), ESLint, Prettier | |

### Infra and workflow

Git + GitHub, GitHub Actions (CI, plus release builds on Windows/macOS/Linux runners), pre-commit, Makefile or `just`. Installers: Inno Setup (Windows, optional), `create-dmg` (macOS), `tar.gz`/AppImage (Linux). Optional: Docker Compose (contributors and self-hosting), Langfuse (self-hosted) for prompt tracing.

---

## 4. Repo layout

```
gamma-clone/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/            # routers: decks, generate, ai, agent, export, import, settings, assets
│  │  ├─ core/           # config, security, logging, errors
│  │  ├─ models/         # SQLAlchemy models
│  │  ├─ schemas/        # Pydantic: Deck, Card, Block, Theme, Layout, Outline, EditOps
│  │  ├─ services/
│  │  │  ├─ llm/         # gateway, capability registry, structured output, repair
│  │  │  ├─ generation/  # outline, card generation, layout selection
│  │  │  ├─ images/      # provider interface + implementations
│  │  │  ├─ export/      # pdf/png (Playwright), pptx, html
│  │  │  ├─ importers/   # text, pdf, docx, url
│  │  │  └─ agent/       # edit ops + tool loop
│  │  ├─ prompts/        # Jinja2 templates
│  │  └─ layouts/        # layout specs (shared source for React + PPTX)
│  ├─ tests/
│  ├─ alembic/
│  └─ pyproject.toml
├─ frontend/
│  ├─ src/
│  │  ├─ api/            # generated client
│  │  ├─ components/     # blocks, layouts, editor, sidebar, dialogs
│  │  ├─ pages/          # home, editor, present, print, settings
│  │  ├─ themes/         # design tokens
│  │  └─ store/
│  └─ package.json
├─ launcher/             # production entrypoint: free port, start server, open browser
├─ desktop/              # Tauri project: native window wrapping the backend sidecar (Phase 9)
├─ packaging/            # PyInstaller spec, icons, installer scripts (Inno Setup, dmg)
├─ evals/                # model benchmark + generation quality suite
├─ data/                 # dev only (gitignored); shipped builds use the OS app-data folder
├─ docs/
├─ docker-compose.yml    # optional: dev / self-hosting
├─ Dockerfile            # optional
├─ Makefile
└─ README.md
```

---

## 5. Core data model and API sketch

### Deck JSON (what the LLM produces and the renderer consumes)

```json
{
  "id": "deck_01",
  "title": "Why local-first AI tools matter",
  "theme": "ocean",
  "cards": [
    {
      "id": "c1",
      "layout": "two_column",
      "blocks": [
        { "type": "heading", "text": "Why local-first?" },
        { "type": "bullets", "items": ["Privacy by default", "Works offline"] },
        { "type": "image", "prompt": "abstract laptop with glowing chip", "asset_id": null }
      ]
    }
  ]
}
```

Keep the block set small and the fields flat. Small local models produce valid JSON far more reliably against simple schemas. Put `max_length` limits on text fields so cards don't overflow.

### API sketch

| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/api/decks` | List / create decks |
| GET / PATCH / DELETE | `/api/decks/{id}` | Read / autosave / delete |
| POST | `/api/generate/outline` | Prompt (or imported text) to outline |
| POST | `/api/generate/deck` | Outline to cards, **SSE stream** |
| POST | `/api/cards/{id}/regenerate` | Regenerate one card |
| POST | `/api/ai/edit` | Rewrite / shorten / expand / translate a block or card |
| POST | `/api/agent/chat` | Chat agent returning edit operations |
| POST | `/api/decks/{id}/export?format=pdf\|pptx\|png\|html` | Export |
| POST | `/api/import` | Text / PDF / DOCX / URL to outline |
| GET / PUT | `/api/settings/providers` | Provider config (keys write-only) |
| POST | `/api/settings/providers/test` | Test a connection |
| GET | `/api/providers/ollama/models` | List installed Ollama models |
| GET | `/api/system/status` | First-run checks: Ollama reachable, PDF browser available, data folder path, app version |
| GET | `/api/assets/{id}` | Serve generated/uploaded images |

---

## 6. Phases and tasks

Task IDs (P0.1, P1.3, ...) are meant to become GitHub issues.

### Phase 0: Foundation (2-3 days)

- [x] **P0.1** Create the git repo, `.gitignore`, license, README skeleton
- [x] **P0.2** Backend scaffold: `uv init`, FastAPI app, `/health`, pydantic-settings config
- [x] **P0.3** Frontend scaffold: Vite + React + TS, Tailwind, shadcn/ui, React Router
- [x] **P0.4** Tooling: Ruff, mypy/pyright, pytest; ESLint, Prettier, Vitest; pre-commit hooks
- [x] **P0.5** Contract pipeline: export OpenAPI, generate the TS client (`make gen-api`)
- [x] **P0.6** Dev commands: `make dev` runs both servers; Vite proxy to FastAPI
- [x] **P0.7** CI: GitHub Actions running lint, type-check and tests for both sides
- [x] **P0.8** Decide the project name and MVP scope (presentations only)

**Done when:** `make dev` boots both apps, the UI can call `/health`, and CI is green.

### Phase 1: Document model and renderer, no AI (1.5-2.5 weeks)

- [x] **P1.1** Pydantic models: `Deck`, `Card`, `Block` (discriminated union on `type`), `Theme`, layout enum, with text length limits
- [x] **P1.2** SQLAlchemy model + Alembic migration for decks (JSON column)
- [x] **P1.3** CRUD endpoints for decks
- [x] **P1.4** Layout specs as data (regions and slots), shared by React and the future PPTX exporter
- [x] **P1.5** React block components: heading, paragraph, bullets, columns, quote, stat, table, image, chart placeholder
- [x] **P1.6** Build 6-8 layouts (title, two-column, three-box, image-left/right, quote, timeline, ...)
- [x] **P1.7** Theme tokens to CSS variables; 3 themes; theme switcher
- [x] **P1.8** Seed 2-3 hand-written decks; scroll view plus presentation mode (fullscreen, arrow keys)
- [x] **P1.9** App paths and production serving: `platformdirs`-based data directory (env-var override for dev); FastAPI serves the built React files in production mode
- [x] **P1.10** **Packaging spike (de-risk early):** minimal `launcher/main.py` (pick a free port, start Uvicorn on `127.0.0.1`, open the browser) plus a PyInstaller `--onedir` build in CI on Windows, macOS and Linux; run each bundle and hit `/api/health`. Finding bundling problems now is far cheaper than after Phase 7.

**Done when:** a hand-written deck renders well, themes switch cleanly, presentation mode works, and a CI-built bundle launches on all three operating systems. This is the foundation everything else sits on; do not skip it.

### Phase 2: LLM provider layer (1 week)

- [x] **P2.1** Provider settings model and API; keys stored in the OS keyring (encrypted-file fallback), write-only from the frontend
- [x] **P2.2** LiteLLM wrapper with async `complete()` and `stream()`
- [x] **P2.3** `generate_structured(PydanticModel, messages)` using Instructor or JSON-schema `response_format` (Ollama `format` field for local)
- [x] **P2.4** Model capability registry (supports JSON schema? tools? context window?) and a fallback ladder: native schema, then JSON mode, then prompt-only plus repair
- [x] **P2.5** JSON repair, validation, and retry with the validation error fed back to the model
- [x] **P2.6** Ollama integration: list installed models, connection test, clear errors (server down, model not pulled)
- [x] **P2.7** Frontend settings page: add provider, test connection, pick default models per role (outline / content / edit)
- [x] **P2.8** Benchmark script (`evals/`): fixed prompts against each configured model, reporting valid-JSON rate, latency, tokens
- [x] **P2.9** Timeouts, cancellation, rate-limit backoff, rough token/cost estimate
- [x] **P2.10** Bundle check: rebuild the PyInstaller bundle and confirm the gateway still works inside it (LiteLLM ships data files that PyInstaller misses by default). If it is too large or fragile, fall back to thin per-provider adapters over `httpx`.

**Done when:** the same structured call succeeds on Gemini, Claude, Grok and at least one Ollama model, and the benchmark prints a comparison.

### Phase 3: Generation pipeline (1-2 weeks)

- [x] **P3.1** Jinja2 prompt templates (outline, card) parameterized by tone, language, audience, card count, text density
- [x] **P3.2** Outline service and endpoint returning an `Outline` schema
- [x] **P3.3** Outline editor UI (edit, reorder, add, delete) before full generation
- [x] **P3.4** Per-card generation with a configurable concurrency limit (parallel for cloud, sequential for weak local hardware)
- [x] **P3.5** Layout selection: LLM hint validated against the layout enum, with a deterministic fallback based on block shapes
- [x] **P3.6** SSE stream (`outline`, `card`, `error`, `done` events); frontend renders cards as they arrive
- [x] **P3.7** Generation settings UI (card count, tone, language, audience, density)
- [x] **P3.8** Regenerate a single card; handle partial failures without losing the rest
- [x] **P3.9** Generation job record (status, progress) so a page refresh does not lose work

**Done when:** prompt, then editable outline, then complete deck works on one cloud model and one local model.

### Phase 4: Editor and persistence (2-3 weeks)

- [x] **P4.1** Card sidebar: thumbnails, dnd-kit reorder, duplicate, delete, add
- [x] **P4.2** Inline editing with TipTap; block insert menu
- [x] **P4.3** Debounced autosave (PATCH) with a version field for conflict safety
- [x] **P4.4** Undo/redo (Immer patches)
- [x] **P4.5** Inline AI actions (rewrite, shorten, expand, translate, change tone) via `/api/ai/edit`, with accept/reject
- [x] **P4.6** Per-card layout picker; global theme switcher
- [x] **P4.7** Project home: list, search, rename, duplicate, delete

**Done when:** you can generate, edit, close and reopen a deck. **This is your MVP.**

### Phase 5: Images and charts (1-2 weeks)

- [x] **P5.1** Image provider interface `generate(prompt, size) -> bytes` with implementations: cloud image API, ComfyUI/A1111 (local), Unsplash/Pexels (stock)
- [x] **P5.2** Asset storage on disk (`data/assets/`), served by FastAPI, referenced by ID
- [x] **P5.3** LLM step that writes image prompts from card content, with a style hint derived from the theme
- [x] **P5.4** Async image jobs: placeholder first, then SSE update; regenerate, replace, upload
- [x] **P5.5** Chart block: data in JSON, rendered by Recharts; mark model-generated numbers as illustrative to avoid implying real data
- [x] **P5.6** Mermaid diagram block; Lucide icons
- [x] **P5.7** Graceful fallback when no image provider is configured (gradients, patterns, icons)

### Phase 6: Import and export (2 weeks)

- [x] **P6.1** `/print/:deckId` route in React with page-sized CSS
- [x] **P6.2** PDF and PNG export via Playwright hitting the print route, using the user's installed Chrome/Edge (`channel="chrome"` / `"msedge"`) and falling back to downloading Chromium into the app-data folder on first export (with a progress message). Verify it works inside the PyInstaller bundle.
- [x] **P6.3** PPTX export with python-pptx driven by the layout specs; verify in PowerPoint and LibreOffice; accept some fidelity loss
- [x] **P6.4** Standalone HTML export (inlined CSS, JS, assets)
- [x] **P6.5** Import: paste text into the outline step
- [x] **P6.6** Import: PDF, DOCX, URL, with an SSRF guard (block private/loopback addresses)
- [x] **P6.7** Long-input handling: chunk and summarize (map-reduce) so small-context models cope
- [x] **P6.8** (Optional) PPTX import

### Phase 7: Chat agent (1-2 weeks)

- [x] **P7.1** Define edit operations (JSON Patch or custom): `add_card`, `update_block`, `move_card`, `delete_card`, `set_layout`, `set_theme`
- [x] **P7.2** Agent loop: LLM tool calling, validate ops, apply to a copy, return a preview
- [x] **P7.3** Chat panel UI with accept/reject; one accepted turn equals one undo step
- [x] **P7.4** Fallback for models without tool calling: ask for an ops list via structured output
- [x] **P7.5** Guardrails: max ops per turn, schema validation, confirmation before deletions

### Phase 8: Launcher packaging, quality and first release (2-3 weeks)

**Packaging and release**
- [x] **P8.1** Launcher hardening: free-port selection with fallback, single-instance lock (a second launch just opens the browser tab to the running app), graceful shutdown (console window or tray icon with "Quit"), log file in the app-data folder, `--port` / `--no-browser` flags
- [x] **P8.2** First-run experience: welcome screen; detect Ollama (running? models pulled? link to install) or guide the user through adding an API key; show where their data is stored
- [x] **P8.3** Final PyInstaller spec: `--onedir` (faster startup and fewer antivirus false positives than `--onefile`); bundle the built frontend, prompts, layout specs and Alembic migrations; `collect-all` / hidden imports for LiteLLM and Playwright; app icon and version stamp
- [x] **P8.4** Automatic DB migrations on startup (Alembic `upgrade head`), with a backup copy of the DB file before migrating when the app version changed
- [x] **P8.5** Per-OS artifacts on CI: Windows (zip, optional Inno Setup installer), macOS (`.app` in a `.dmg`; Apple Silicon and Intel built separately or via a universal2 Python), Linux (`tar.gz`, optional AppImage). Smoke-test every artifact: launch it, wait for `/api/health`, shut it down.
- [x] **P8.6** Release workflow: on a `v*` tag, build all artifacts, generate SHA256 checksums, attach everything to a GitHub Release with generated notes
- [x] **P8.7** Signing (optional for early releases): document the Windows SmartScreen and macOS Gatekeeper "unidentified developer" steps; later add a Windows code-signing certificate and Apple Developer ID plus notarization
- [x] **P8.8** Update check: on launch, ask the GitHub Releases API for the latest version and show a non-intrusive "new version available" banner linking to the download page. No auto-updater in v1; provide a setting to turn the check off.

**Quality and docs**
- [x] **P8.9** Eval suite (about 20 prompts per model): valid-JSON rate, text overflow rate, layout variety, latency
- [x] **P8.10** E2E tests (Playwright): generate, edit, export
- [x] **P8.11** Error UX: missing key, Ollama offline, model not pulled, context overflow, port in use
- [x] **P8.12** Docs: per-OS quickstart, "add a provider", troubleshooting (antivirus, ports, Ollama), where data lives; add a Download section to the README
- [x] **P8.13** Download page (GitHub Pages or a simple site): per-OS buttons, screenshots, checksums
- [x] **P8.14** (Optional) Dockerfile and `docker-compose.yml` (app plus optional `ollama` profile) for contributors and self-hosting

**Done when:** a non-technical person can download a file from the release page, double-click it, configure a model in the first-run screen, and generate a deck, with no terminal involved.

### Phase 9: Desktop app (Tauri) — a second, native download option (3-4 weeks)

The launcher (Phase 8) stays as the lightweight, no-install option. This phase adds an **installed desktop app** alongside it, so the download page offers both per OS. The desktop app is the same backend and frontend, run inside a native window instead of the browser — not a second implementation.

**Shell choice: Tauri over Electron.** Tauri uses the OS's built-in webview (WebView2 on Windows, WKWebView on macOS, WebKitGTK on Linux), so the shell itself adds only a few MB, versus Electron bundling its own Chromium (100-150+ MB). Since the Python backend is already bundled via PyInstaller, Tauri's job is just to start it and open a window — it doesn't need Node.js integration, which is Electron's main advantage and not needed here. Revisit Electron only if Tauri's sidecar or webview support proves too limiting.

**Group A — Decision and architecture**
- [x] **P9.1** Write a short decision note (Tauri vs Electron trade-offs: size, resource use, sidecar maturity, webview-version fragmentation); confirm Tauri
- [x] **P9.2** Confirm the architecture: Tauri window loads `http://127.0.0.1:<port>`, served by the same PyInstaller backend from Phase 8, started as a sidecar; no new business logic

**Group B — Project setup**
- [x] **P9.3** Scaffold `desktop/` with `cargo tauri init`, pointed at the built `frontend/dist` (used only for icons/config; the window navigates to the live local URL rather than loading static files directly)
- [x] **P9.4** Configure `tauri.conf.json`: `bundle.externalBin` referencing the PyInstaller backend binary per target triple, app identifier, icon set, window title and minimum size
- [x] **P9.5** Rust-side sidecar manager: spawn the backend on app startup, poll `/api/health` until ready, kill the child process (including a force-kill fallback) on window close or app quit, surface a retry/error dialog if the backend crashes or the port is unavailable
- [x] **P9.6** Single-instance plugin: a second launch focuses the existing window instead of starting a second backend process
- [x] **P9.7** Native splash/loading screen shown while the sidecar boots (cold start can take a few seconds)

**Group C — Native integration**
- [x] **P9.8** System tray icon (Show / Hide / Quit) with a "minimize to tray" setting
- [x] **P9.9** Minimal native menu bar (Quit, standard Edit commands, Check for Updates, About)
- [ ] **P9.10** Native save dialogs for PDF/PPTX/PNG export (Tauri's dialog and fs plugins) in place of the browser download flow; the launcher keeps the browser-download behavior
- [ ] **P9.11** *(Optional, cut if unneeded)* `deck://` deep-link handler for opening a deck from outside the app

**Group D — Updates and signing**
- [ ] **P9.12** Tauri updater plugin wired to a signed `latest.json` manifest published alongside each GitHub Release; generate the updater signing keypair and store the private key in GitHub Actions secrets (configuration and procedure are documented; no signed key/manifest exists yet)
- [ ] **P9.13** Code signing: Windows Authenticode certificate, macOS Developer ID plus notarization. Needed for the updater to run without scary prompts, and reusable for the Phase 8 launcher too

**Group E — CI/CD and release**
- [x] **P9.14** Extend the release workflow to also build Tauri bundles on native runners: Windows (`.msi`/`.exe`), macOS (`.dmg`, arm64 and x64 or universal2), Linux (`.deb`, `.AppImage`) — alongside the existing plain-launcher artifacts, not replacing them
- [ ] **P9.15** CI smoke test per platform: install/run the bundle, confirm the sidecar starts and `/api/health` responds inside the shell
- [x] **P9.16** Update the download page to present both options per OS with a one-line "which should I pick" note (desktop app: installed, auto-updates, native feel; launcher: no install, just unzip and run)

**Group F — Docs and maintenance**
- [x] **P9.17** Desktop-specific troubleshooting docs: missing WebKitGTK on Linux (`apt install` step), missing WebView2 runtime on older Windows, Gatekeeper/notarization messaging
- [x] **P9.18** Decide and document the maintenance policy: both tracks get every release, or the launcher moves to maintenance-only once the desktop app is stable

**Done when:** both the launcher and the desktop app are on the release page for Windows, macOS and Linux; the desktop app opens as a native window with no visible browser chrome; auto-update works end to end on at least one OS; quitting the app leaves no orphaned backend process.

### Phase 10: Polish and extras (ongoing)

- [ ] Templates and brand kit (logo, colors, fonts)
- [ ] Documents and webpage output types
- [ ] Speaker notes and presenter view
- [ ] Keyboard shortcuts, UI localization

---

## 7. Timeline (solo developer, rough)

| Milestone | Phases | Estimate |
|---|---|---|
| Foundation | 0 | 2-3 days |
| **MVP** (generate, edit, reopen) | 0-4 | 7-10 weeks |
| Images, import/export, agent | 5-7 | 4-6 weeks |
| Launcher packaging and first release | 8 | 2-3 weeks |
| **Full product (v1 — launcher)** | 0-8 | about 13-19 weeks |
| Desktop app (Tauri) | 9 | 3-4 weeks |
| **v1.1 — launcher + desktop app** | 0-9 | about 16-23 weeks |

---

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Small local models break JSON | Flat schema, per-card generation, constrained decoding (Ollama `format`), validation plus retry with error feedback, benchmark early (P2.8) |
| PPTX fidelity | Layouts defined as data (P1.4), budget time, accept simplifications, test in real PowerPoint |
| Text overflow in cards | `max_length` in Pydantic fields, length rules in prompts, overflow metric in evals |
| Slow generation on local hardware | Concurrency setting, streaming so the user sees progress, smaller model option for outline step |
| Model hallucinated chart data | Label as illustrative; let the user edit the numbers |
| SSRF via URL import | Block private, loopback and link-local IPs; limit redirects and size |
| API key leakage | Encrypt at rest, write-only endpoints, never log keys or full prompts containing them |
| PyInstaller bundle breaks (missing data files, hidden imports; LiteLLM and Playwright are the usual culprits) | Packaging spike in Phase 1 (P1.10), smoke-test every artifact in CI, rebuild after each new dependency; fall back to thin `httpx` adapters if LiteLLM is too fragile |
| Antivirus false positives and SmartScreen warnings on unsigned builds | Use `--onedir`, publish SHA256 checksums, document the warning screens, sign later |
| macOS Gatekeeper blocks the unsigned app | Document right-click > Open; notarize once you have an Apple Developer ID |
| Large download (Python plus libraries can reach several hundred MB) | Do not bundle a browser, build in a clean venv, exclude unused packages |
| Local server reachable by other websites or processes | Bind to `127.0.0.1` only, validate `Host`/`Origin`, no wildcard CORS |
| Port already in use, or the app launched twice | Free-port selection and a single-instance lock (P8.1) |
| User data lost on upgrade | Data lives outside the app folder; DB backup before migrations (P8.4) |
| Missing WebView2 (older Windows) or WebKitGTK (Linux) breaks the desktop app | Bundle/prompt for the WebView2 runtime; document the WebKitGTK package for Linux; the launcher remains a fallback that needs neither |
| Sidecar process survives a shell crash or force-quit | Process-group kill on exit, startup check that kills any orphan from a previous crash, tested explicitly in P9.15 |
| Updater signing key lost or leaked | Store it only in CI secrets, document a key-rotation procedure, never commit it |
| Maintaining two shells (launcher and desktop app) doubles the build and QA surface | Both share 100% of backend/frontend code (P9.2); only the shell differs; CI builds and smoke-tests both every release |
| Scope creep | Follow the MVP cut line (Phase 4); nothing from Phase 10 before v1.1 |

---

## 9. Definition of done

**MVP:** a user configures one provider (cloud key or Ollama), generates a deck from a prompt, edits it, and reopens it later.

**v1 (launcher):** MVP plus images, PDF/PPTX/HTML export, file/URL import, chat agent, downloadable per-OS launcher builds on GitHub Releases that a non-technical user can double-click, and documented eval results for at least three models.

**v1.1 (launcher + desktop app):** everything in v1, plus an installed, native desktop app for each OS — built from the same backend and frontend, with its own window, system tray, native export dialogs and working auto-update — offered as a second download option alongside the launcher.
