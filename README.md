# PROJECT_NAME

**Turn a prompt into a polished, editable presentation. Runs on your machine, with the AI model you choose.**

> **Status:** early development. Nothing here is usable yet; this README will grow as each phase of the plan is completed.

PROJECT_NAME is an open-source, local-first AI presentation builder inspired by tools like Gamma. Describe a topic (or paste text, or import a file or URL) and get a card-based presentation you can edit, restyle and export. Bring your own model: use API keys you already have (Gemini, Claude, Grok, ...) or run fully offline with local models through Ollama.

*Not affiliated with or endorsed by Gamma.*

---

## Features

Planned (see the [roadmap](#roadmap)):

- Generate a deck from a prompt, pasted text, or an imported PDF / DOCX / URL
- Editable outline before full generation
- Card-based layouts that grow with their content, plus switchable themes
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
| Tooling | uv, Ruff, pytest, Vitest, Playwright, GitHub Actions, Docker |

## Getting started

> These steps are provisional and will be finalized as the project scaffolding lands.

### Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- *Optional:* [Ollama](https://ollama.com/) for local models
- *Optional:* Docker and Docker Compose

### Run locally

```bash
git clone https://github.com/<your-username>/PROJECT_NAME.git
cd PROJECT_NAME

# Copy the example environment file (once it exists)
cp .env.example .env

# Start backend and frontend (Makefile arrives in Phase 0)
make dev
```

### Choosing a model

Open **Settings** in the app and add a provider:

| Provider | What you need |
|---|---|
| Gemini / Anthropic / xAI | An API key |
| Ollama | A running Ollama server and at least one pulled model |
| OpenAI-compatible | A base URL and (optionally) a key |

API keys are stored locally and encrypted at rest.

## Project structure

```
backend/     FastAPI app (API, LLM gateway, generation, export, import)
frontend/    React app (renderer, editor, settings)
evals/       Model benchmarks and generation-quality checks
docs/        Plan and architecture notes
data/        Local database and generated assets (gitignored)
```

## Roadmap

- [ ] **Phase 0:** Foundation (repo, scaffolding, tooling, CI)
- [ ] **Phase 1:** Document model and renderer
- [ ] **Phase 2:** LLM provider layer
- [ ] **Phase 3:** Generation pipeline
- [ ] **Phase 4:** Editor and persistence *(MVP)*
- [ ] **Phase 5:** Images and charts
- [ ] **Phase 6:** Import and export
- [ ] **Phase 7:** Chat agent
- [ ] **Phase 8:** Packaging and quality *(v1)*

The full task breakdown lives in [`docs/plan.md`](docs/plan.md).

## Contributing

The project is at a very early stage. Issues and ideas are welcome; please open an issue before starting a large pull request.

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for the full text.
