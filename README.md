# Delta

**Turn a prompt into a polished, editable presentation. Runs on your machine, with the AI model you choose.**

> **Status:** Phases 0–8 are in active release preparation. Delta includes an editable presentation MVP with a reviewable chat agent and local import/export.

Delta is an open-source, local-first AI presentation builder inspired by tools like Gamma. Describe a topic (or paste text, or import a file or URL) and get a card-based presentation you can edit, restyle and export. Bring your own model: use API keys you already have (Gemini, Claude, Grok, ...) or run fully offline with local models through Ollama.

*Not affiliated with or endorsed by Gamma.*

---

## Features

Available now:

- Browse three hand-written demo decks in the local presentation library
- Render validated card documents with eight shared layouts and nine block types
- Switch between Ocean, Sunset, and Forest themes; theme changes persist locally
- Scroll through a deck or use presentation mode with arrow-key navigation
- Create, read, update, and delete decks through the local API
- Configure Gemini, Claude, Grok, OpenAI-compatible endpoints, or local Ollama
- Set separate default models for outline, card content, and editing tasks
- Stream or complete asynchronous model calls through a shared LiteLLM gateway, with structured JSON validation and repair
- Benchmark configured models for JSON validity, latency, tokens, and estimated cost
- Generate an outline from a prompt with configurable tone, language, audience, card count, and density
- Edit, reorder, add, or remove outline items before generating cards
- Stream generated cards over SSE with persistent job progress and partial-failure recovery
- Regenerate an individual card without discarding successfully generated cards
- Edit cards inline with add, duplicate, delete, reorder, layout and theme controls
- Autosave with optimistic version conflict safety, undo/redo, and accept/reject AI edits
- Reviewable whole-deck chat edits with bounded operations and deletion confirmation
- Search, rename, duplicate, and delete presentations from the project home
- Image assets with upload, persistent asynchronous generation jobs, SSE updates, and
  OpenAI-compatible, A1111/ComfyUI, Unsplash/Pexels, or offline SVG fallback providers
- JSON chart blocks (explicitly marked illustrative), Mermaid diagram blocks, and Lucide icons
- Print-ready `/print/:deckId` pages plus PDF, PNG, PPTX, and standalone HTML export APIs
- Paste-text, PDF, PPTX, DOCX, and URL imports; PPTX imports extract slide and table text, while URL imports block private, loopback, link-local, and reserved addresses

Planned (see the [roadmap](#roadmap)):
- AI-generated images and charts
- Cloud models **or** local models, configured in the app's settings
- Local-first: your decks and API keys stay on your machine

## How it works

The AI does not design slides. It writes a **structured document (JSON)**, and a deterministic renderer plus a design system turns that structure into visuals. That is what makes the model swappable.

```
Input -> Outline -> Card content (JSON) -> Layout -> Theme -> Images/Charts -> Editor -> Export
```

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy + Alembic, SQLite |
| LLM access | LiteLLM (Gemini, Anthropic, xAI, OpenAI-compatible, Ollama) |
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui, TipTap |
| Export | Playwright (PDF/PNG), python-pptx (PPTX) |
| Tooling | uv, Ruff, mypy, pytest, ESLint, Prettier, Vitest, pre-commit, GitHub Actions |

## Getting started

### Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 22+ (or 20.19+) and npm
- *Optional:* [Ollama](https://ollama.com/) for local models
- *Optional:* Docker and Docker Compose

### Run locally

```bash
git clone https://github.com/FanisD/Delta.git
cd Delta

# Copy the example environment file
cp .env.example .env

# Install dependencies, install hooks, and start backend and frontend
uv sync --project backend
npm ci --prefix frontend
make hooks-install
make dev
```

The frontend is available at <http://127.0.0.1:5173>; the API and OpenAPI schema
are served at <http://127.0.0.1:8000>. Run `make gen-api` to regenerate the
typed frontend API client from the backend contract, and `make check` to run
linting, formatting checks, type checks, and tests.

### Download and launcher

Tagged releases publish per-platform `Delta` archives from GitHub Actions. Extract
the archive and double-click `Delta` (or run `Delta --no-browser` for server-only
launch). The launcher chooses a free loopback port, writes logs and the database
under the platform's Delta application-data directory, and a second launch opens
the existing tab. `--port 8000` requests a preferred port but falls back safely.

Unsigned early builds may show Windows SmartScreen (**More info → Run anyway**) or
macOS Gatekeeper (**Control-click → Open** once). Linux users should run the
extracted executable and verify the published SHA256 checksum if antivirus flags it.
If Ollama is offline, start it and pull a model (`ollama pull qwen2.5:7b`) before
selecting it in Settings.

### Model providers

Open **Settings** in the app to configure one or more providers:

| Provider | Configuration |
|---|---|
| Gemini / Anthropic / xAI | Model name and API key |
| Ollama | A running Ollama server; use **Find installed models** |
| OpenAI-compatible | Model name and endpoint base URL; API key is optional |

Cloud API keys are write-only in the UI and encrypted in SQLite using Fernet. Before saving a cloud key, set `APP_ENCRYPTION_KEY` in the root `.env` file. Generate a key once:

```bash
uv run --project backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep this key private and back it up separately from the database; losing or changing it makes saved provider keys unreadable. After configuring models, run `make benchmark` to print a JSON comparison. Real provider calls require valid provider credentials and, for Ollama, a running server with the selected model installed.

### Generation flow

Choose **Create with AI**, enter a topic and generation settings, then edit the generated
outline before starting card generation. Cards stream into the UI over SSE, while persistent
jobs expose status and progress after a refresh. The API also supports regenerating one card
without discarding the other generated cards.

### Import and export

Use `/print/<deck-id>` for a page-sized print view. The backend exposes
`/api/decks/<deck-id>/export/{pdf,png,pptx,html}`. PDF/PNG export prefers an
installed Chrome or Edge and attempts a first-use Chromium download under the
Delta app-data directory when neither is available. PPTX export intentionally
maps the structured document to editable text boxes and may lose visual fidelity.
Imports are available at `/api/import/text`, `/api/import/file`, and
`/api/import/url`; remote fetches have strict size, timeout, redirect, and SSRF
protections.

## Project structure

```
backend/     FastAPI app (API, LLM gateway, generation, export, import)
frontend/    React app (renderer, editor, settings)
evals/       Model benchmarks and generation-quality checks
plan.md      Plan and architecture notes
data/        Local database and generated assets (gitignored)
```

## Download and self-hosting

Download platform archives from the [Delta Releases page](https://github.com/FanisD/Delta/releases)
or the [download page](docs/download/index.html). Release archives include SHA256 checksums;
cross-platform artifact launch checks run in GitHub Actions, while local development can use
`python packaging/smoke.py <path-to-Delta>`.

Contributors can run `docker compose up --build`. Add `--profile ollama` to start an Ollama
container alongside Delta (`docker compose --profile ollama up --build`), then pull a model
from the Ollama container.

## Roadmap

- [x] **Phase 0:** Foundation (repo, scaffolding, tooling, CI)
- [x] **Phase 1:** Document model, renderer, app-data paths, and launcher spike
- [x] **Phase 2:** LLM provider layer and bundle smoke path
- [x] **Phase 3:** Generation pipeline
- [x] **Phase 4:** Editor and persistence *(MVP)*
- [x] **Phase 5:** Images and charts
- [x] **Phase 6:** Import and export
- [x] **Phase 7:** Chat agent
- [ ] **Phase 8:** Packaging and quality *(launcher, packaging workflow, and docs implemented; update UI, first-run screen, and full cross-platform release validation remain)*

The full task breakdown lives in [`plan.md`](plan.md).

## Contributing

The project is at a very early stage. Issues and ideas are welcome; please open an issue before starting a large pull request.

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for the full text.
