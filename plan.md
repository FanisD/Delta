# Gamma-Style AI Presentation Builder: Build Plan

**Stack:** FastAPI (Python) backend + React (TypeScript) frontend
**Runs:** locally, with either cloud model API keys (Gemini, Claude, Grok, ...) or local models (Ollama, ...)

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
3. **PDF/PNG export renders the React app.** The backend opens a `/print/:deckId` route in headless Chromium (Playwright). In production FastAPI serves the built React files so this works in one container.
4. **Generation streams over SSE** (Server-Sent Events), so cards appear as they are generated.
5. **One LLM gateway module** (LiteLLM) so no other code knows which provider is in use.

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
| Secrets | `cryptography` (Fernet) or `keyring` | API keys encrypted at rest, never returned to the frontend |
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

Git + GitHub, GitHub Actions (CI), pre-commit, Makefile or `just`, Docker + Docker Compose, optional Langfuse (self-hosted) for prompt tracing.

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
├─ evals/                # model benchmark + generation quality suite
├─ data/                 # (gitignored) SQLite DB + generated assets
├─ docs/
├─ docker-compose.yml
├─ Dockerfile
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
| GET | `/api/assets/{id}` | Serve generated/uploaded images |

---

## 6. Phases and tasks

Task IDs (P0.1, P1.3, ...) are meant to become GitHub issues.

### Phase 0: Foundation (2-3 days)

- [ ] **P0.1** Create the git repo, `.gitignore`, license, README skeleton
- [ ] **P0.2** Backend scaffold: `uv init`, FastAPI app, `/health`, pydantic-settings config
- [ ] **P0.3** Frontend scaffold: Vite + React + TS, Tailwind, shadcn/ui, React Router
- [ ] **P0.4** Tooling: Ruff, mypy/pyright, pytest; ESLint, Prettier, Vitest; pre-commit hooks
- [ ] **P0.5** Contract pipeline: export OpenAPI, generate the TS client (`make gen-api`)
- [ ] **P0.6** Dev commands: `make dev` runs both servers; Vite proxy to FastAPI
- [ ] **P0.7** CI: GitHub Actions running lint, type-check and tests for both sides
- [ ] **P0.8** Decide the project name and MVP scope (presentations only)

**Done when:** `make dev` boots both apps, the UI can call `/health`, and CI is green.

### Phase 1: Document model and renderer, no AI (1-2 weeks)

- [ ] **P1.1** Pydantic models: `Deck`, `Card`, `Block` (discriminated union on `type`), `Theme`, layout enum, with text length limits
- [ ] **P1.2** SQLAlchemy model + Alembic migration for decks (JSON column)
- [ ] **P1.3** CRUD endpoints for decks
- [ ] **P1.4** Layout specs as data (regions and slots), shared by React and the future PPTX exporter
- [ ] **P1.5** React block components: heading, paragraph, bullets, columns, quote, stat, table, image, chart placeholder
- [ ] **P1.6** Build 6-8 layouts (title, two-column, three-box, image-left/right, quote, timeline, ...)
- [ ] **P1.7** Theme tokens to CSS variables; 3 themes; theme switcher
- [ ] **P1.8** Seed 2-3 hand-written decks; scroll view plus presentation mode (fullscreen, arrow keys)

**Done when:** a hand-written deck renders well, themes switch cleanly, and presentation mode works. This is the foundation everything else sits on; do not skip it.

### Phase 2: LLM provider layer (1 week)

- [ ] **P2.1** Provider settings model and API; keys encrypted at rest, write-only from the frontend
- [ ] **P2.2** LiteLLM wrapper with async `complete()` and `stream()`
- [ ] **P2.3** `generate_structured(PydanticModel, messages)` using Instructor or JSON-schema `response_format` (Ollama `format` field for local)
- [ ] **P2.4** Model capability registry (supports JSON schema? tools? context window?) and a fallback ladder: native schema, then JSON mode, then prompt-only plus repair
- [ ] **P2.5** JSON repair, validation, and retry with the validation error fed back to the model
- [ ] **P2.6** Ollama integration: list installed models, connection test, clear errors (server down, model not pulled)
- [ ] **P2.7** Frontend settings page: add provider, test connection, pick default models per role (outline / content / edit)
- [ ] **P2.8** Benchmark script (`evals/`): fixed prompts against each configured model, reporting valid-JSON rate, latency, tokens
- [ ] **P2.9** Timeouts, cancellation, rate-limit backoff, rough token/cost estimate

**Done when:** the same structured call succeeds on Gemini, Claude, Grok and at least one Ollama model, and the benchmark prints a comparison.

### Phase 3: Generation pipeline (1-2 weeks)

- [ ] **P3.1** Jinja2 prompt templates (outline, card) parameterized by tone, language, audience, card count, text density
- [ ] **P3.2** Outline service and endpoint returning an `Outline` schema
- [ ] **P3.3** Outline editor UI (edit, reorder, add, delete) before full generation
- [ ] **P3.4** Per-card generation with a configurable concurrency limit (parallel for cloud, sequential for weak local hardware)
- [ ] **P3.5** Layout selection: LLM hint validated against the layout enum, with a deterministic fallback based on block shapes
- [ ] **P3.6** SSE stream (`outline`, `card`, `error`, `done` events); frontend renders cards as they arrive
- [ ] **P3.7** Generation settings UI (card count, tone, language, audience, density)
- [ ] **P3.8** Regenerate a single card; handle partial failures without losing the rest
- [ ] **P3.9** Generation job record (status, progress) so a page refresh does not lose work

**Done when:** prompt, then editable outline, then complete deck works on one cloud model and one local model.

### Phase 4: Editor and persistence (2-3 weeks)

- [ ] **P4.1** Card sidebar: thumbnails, dnd-kit reorder, duplicate, delete, add
- [ ] **P4.2** Inline editing with TipTap; block insert menu
- [ ] **P4.3** Debounced autosave (PATCH) with a version field for conflict safety
- [ ] **P4.4** Undo/redo (Immer patches)
- [ ] **P4.5** Inline AI actions (rewrite, shorten, expand, translate, change tone) via `/api/ai/edit`, with accept/reject
- [ ] **P4.6** Per-card layout picker; global theme switcher
- [ ] **P4.7** Project home: list, search, rename, duplicate, delete

**Done when:** you can generate, edit, close and reopen a deck. **This is your MVP.**

### Phase 5: Images and charts (1-2 weeks)

- [ ] **P5.1** Image provider interface `generate(prompt, size) -> bytes` with implementations: cloud image API, ComfyUI/A1111 (local), Unsplash/Pexels (stock)
- [ ] **P5.2** Asset storage on disk (`data/assets/`), served by FastAPI, referenced by ID
- [ ] **P5.3** LLM step that writes image prompts from card content, with a style hint derived from the theme
- [ ] **P5.4** Async image jobs: placeholder first, then SSE update; regenerate, replace, upload
- [ ] **P5.5** Chart block: data in JSON, rendered by Recharts; mark model-generated numbers as illustrative to avoid implying real data
- [ ] **P5.6** Mermaid diagram block; Lucide icons
- [ ] **P5.7** Graceful fallback when no image provider is configured (gradients, patterns, icons)

### Phase 6: Import and export (2 weeks)

- [ ] **P6.1** `/print/:deckId` route in React with page-sized CSS
- [ ] **P6.2** PDF and PNG export via Playwright hitting the print route
- [ ] **P6.3** PPTX export with python-pptx driven by the layout specs; verify in PowerPoint and LibreOffice; accept some fidelity loss
- [ ] **P6.4** Standalone HTML export (inlined CSS, JS, assets)
- [ ] **P6.5** Import: paste text into the outline step
- [ ] **P6.6** Import: PDF, DOCX, URL, with an SSRF guard (block private/loopback addresses)
- [ ] **P6.7** Long-input handling: chunk and summarize (map-reduce) so small-context models cope
- [ ] **P6.8** (Optional) PPTX import

### Phase 7: Chat agent (1-2 weeks)

- [ ] **P7.1** Define edit operations (JSON Patch or custom): `add_card`, `update_block`, `move_card`, `delete_card`, `set_layout`, `set_theme`
- [ ] **P7.2** Agent loop: LLM tool calling, validate ops, apply to a copy, return a preview
- [ ] **P7.3** Chat panel UI with accept/reject; one accepted turn equals one undo step
- [ ] **P7.4** Fallback for models without tool calling: ask for an ops list via structured output
- [ ] **P7.5** Guardrails: max ops per turn, schema validation, confirmation before deletions

### Phase 8: Packaging and quality (1-2 weeks)

- [ ] **P8.1** Multi-stage Dockerfile: build React, serve it from FastAPI, install Playwright browsers
- [ ] **P8.2** `docker-compose.yml`: app plus optional `ollama` service (compose profile) and a volume for `data/`
- [ ] **P8.3** Eval suite (about 20 prompts per model): valid-JSON rate, text overflow rate, layout variety, latency
- [ ] **P8.4** E2E tests (Playwright): generate, edit, export
- [ ] **P8.5** Error UX: missing key, Ollama offline, model not pulled, context overflow
- [ ] **P8.6** Docs: quickstart (cloud keys and Ollama), architecture, "add a provider"
- [ ] **P8.7** Release: version tag, GitHub release, screenshots or demo GIF

### Phase 9: Polish and extras (ongoing)

- [ ] Templates and brand kit (logo, colors, fonts)
- [ ] Documents and webpage output types
- [ ] Speaker notes and presenter view
- [ ] Keyboard shortcuts, UI localization
- [ ] Optional desktop wrapper (Tauri with a bundled Python sidecar; expect packaging pain)

---

## 7. Timeline (solo developer, rough)

| Milestone | Phases | Estimate |
|---|---|---|
| Foundation | 0 | 2-3 days |
| **MVP** (generate, edit, reopen) | 0-4 | 6-9 weeks |
| Images, import/export, agent | 5-7 | 4-6 weeks |
| Packaging and release | 8 | 1-2 weeks |
| **Full product (v1)** | 0-8 | about 12-17 weeks |

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
| Scope creep | Follow the MVP cut line (Phase 4); nothing from Phase 9 before v1 |

---

## 9. Definition of done

**MVP:** a user configures one provider (cloud key or Ollama), generates a deck from a prompt, edits it, and reopens it later.

**v1:** MVP plus images, PDF/PPTX/HTML export, file/URL import, chat agent, one-command Docker run, documented eval results for at least three models.
