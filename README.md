# Delta

**Turn a prompt into a polished, editable presentation. Runs on your machine, with the AI model you choose.**

> **Status:** Phases 0 and 1 are complete, and the Phase 2 provider layer is implemented. Delta includes a local deck library, encrypted provider settings, a multi-provider async LLM gateway, structured-output validation, and a model benchmark. AI presentation generation and editing are planned for later phases.

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

Planned (see the [roadmap](#roadmap)):

- Generate a deck from a prompt, pasted text, or an imported PDF / DOCX / URL
- Editable outline before full generation
- Inline AI editing (rewrite, shorten, expand, translate) and a chat agent for whole-deck changes
- AI-generated images and charts
- Export to PDF, PNG, PPTX and standalone HTML
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

## Project structure

```
backend/     FastAPI app (API, LLM gateway, generation, export, import)
frontend/    React app (renderer, editor, settings)
evals/       Model benchmarks and generation-quality checks
plan.md      Plan and architecture notes
data/        Local database and generated assets (gitignored)
```

## Roadmap

- [x] **Phase 0:** Foundation (repo, scaffolding, tooling, CI)
- [ ] **Phase 1:** Document model and renderer
- [ ] **Phase 2:** LLM provider layer
- [ ] **Phase 3:** Generation pipeline
- [ ] **Phase 4:** Editor and persistence *(MVP)*
- [ ] **Phase 5:** Images and charts
- [ ] **Phase 6:** Import and export
- [ ] **Phase 7:** Chat agent
- [ ] **Phase 8:** Packaging and quality *(v1)*

The full task breakdown lives in [`plan.md`](plan.md).

## Contributing

The project is at a very early stage. Issues and ideas are welcome; please open an issue before starting a large pull request.

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for the full text.
