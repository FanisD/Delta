# Delta

**Delta turns a prompt into an editable presentation on your own computer.**

Delta is local-first: the application, presentation files, and saved provider
settings live on your machine. You choose whether the AI comes from a cloud
provider using your own API key or from a local Ollama model.

> Delta is not affiliated with or endorsed by OpenAI, Google, Anthropic,
> Ollama, or Gamma.

## What can I use today?

| Option | Works without Docker? | Needs an API key? | Best for |
| --- | --- | --- | --- |
| **Browser, local development** | Yes | No, if using Ollama | Developers and contributors |
| **Browser, downloaded launcher** | Yes | No, if using Ollama | People who want to unzip and run Delta |
| **Browser, Docker** | No | No, if using the Ollama Docker profile | Self-hosting and simple repeatable setup |
| **Installed desktop app** | The Tauri shell is scaffolded; signed downloadable desktop bundles are not published yet | Same provider choices | The future native-window distribution |

The browser versions are usable now. The desktop code is under
[`desktop/`](desktop/) and reuses the same backend and frontend, but release
bundles still require native CI builds, icons, backend sidecars, and signing.
Until those are published, use the downloaded launcher or Docker.

## Choose your AI provider

Delta supports these choices in **Settings**:

- **OpenAI**: enter an OpenAI API key and a model such as `gpt-4o-mini`.
- **Google Gemini**: enter a Gemini API key and a model such as
  `gemini-2.5-flash`.
- **Anthropic Claude**: enter an Anthropic API key and a model such as
  `claude-sonnet-4-5`.
- **Ollama**: install Ollama, start it, and download a model such as
  `qwen2.5:7b`. No cloud key is needed.
- **OpenAI-compatible**: optionally connect another service that exposes an
  OpenAI-compatible API by entering its model, URL, and key.

You can configure more than one provider and choose separate models for
outlines, card content, and editing. Delta never displays a saved key again in
the settings screen. Keys are stored using the operating-system keyring when
available, with encrypted local storage as a fallback.

## Easiest option: download and run the launcher

This is the recommended option for people who do not want to install Python,
Node.js, or Docker.

1. Open the [Delta Releases page](https://github.com/FanisD/Delta/releases).
2. Download the file for your computer:
   - Windows: `.zip`
   - macOS: `.dmg`
   - Linux: `.tar.gz`
3. Extract the archive if necessary.
4. Double-click **Delta**. Delta opens in your browser automatically.
5. Open **Settings**, choose a provider, enter its model and key, and save.
6. Choose **Create with AI**, describe your presentation, and generate it.

For the first release, Windows may show **More info → Run anyway** and macOS
may show an “unidentified developer” warning. This happens because early
artifacts may not be code-signed. Only bypass the warning when the archive came
from the official Delta GitHub Releases page. Verify the published SHA256
checksum when possible.

The launcher keeps data in the normal application-data folder for your
operating system. It does not store your presentations in the downloaded
archive. Use `Delta --no-browser` if you want to start the local server without
opening a browser.

## Browser without Docker: local development

Use this path if you are comfortable installing a few tools or want to
contribute to Delta.

### Install prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js 20.19+ or 22.12+ and npm
- Optional: [Ollama](https://ollama.com/)

### Start Delta

```bash
git clone https://github.com/FanisD/Delta.git
cd Delta
cp .env.example .env
uv sync --project backend
npm ci --prefix frontend
make dev
```

Open <http://127.0.0.1:5173>. The local API runs at
<http://127.0.0.1:8000>.

Stop the servers with `Ctrl+C`.

### Use Ollama locally

1. Install Ollama from <https://ollama.com/download>.
2. Start Ollama.
3. Open a terminal and run:

   ```bash
   ollama pull qwen2.5:7b
   ```

4. In Delta, open **Settings**, choose **Ollama**, click **Find installed
   models**, choose `qwen2.5:7b`, and save it.

If you use a different model, select that model in Settings. Ollama must be
running whenever you generate a presentation.

### Use a cloud provider

Open **Settings**, choose **OpenAI**, **Google Gemini**, or **Anthropic
Claude**, enter the model name and API key, then save and test the provider.
The key is sent only when Delta calls that provider. Cloud providers charge
according to their own pricing; Delta does not include an AI subscription.

If Delta reports that a key cannot be saved, copy `.env.example` to `.env`,
generate an encryption key, and put it after `APP_ENCRYPTION_KEY=`:

```bash
uv run --project backend python -c \
  "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep the resulting key private. Changing or losing it can make encrypted
provider settings unreadable.

## Browser with Docker

Docker runs the backend and built frontend together at
<http://localhost:8000>. This is the easiest browser setup when Docker is
already installed.

### Cloud provider in Docker

```bash
git clone https://github.com/FanisD/Delta.git
cd Delta
docker compose up --build
```

Open <http://localhost:8000>, then configure OpenAI, Gemini, or Anthropic in
**Settings**. Your data is kept in the Docker volume named `delta-data`.

### Ollama in Docker

Start both services:

```bash
docker compose --profile ollama up --build
```

In a second terminal, download a model into the Ollama container:

```bash
docker compose exec ollama ollama pull qwen2.5:7b
```

Open <http://localhost:8000>, choose **Ollama** in Settings, click **Find
installed models**, and save the model. The Ollama model files are kept in the
`ollama-data` Docker volume.

To stop Docker:

```bash
docker compose down
```

The named volumes are not deleted by that command. To delete all Docker data,
including presentations and downloaded models, use
`docker compose down -v`.

## Desktop app

The native app uses Tauri 2 and starts the same packaged Python backend as a
sidecar. It does not contain a second presentation editor or a second AI
implementation. See [`docs/desktop.md`](docs/desktop.md) and the
[Tauri/Electron decision note](docs/desktop-decision.md).

The project currently contains the desktop source and release workflow, but
official signed desktop installers are not yet available in GitHub Releases.
When they are published, the download page will offer both:

- **Desktop app**: installed native window and automatic updates.
- **Launcher**: no installation; unzip and run, then use the browser.

Until then, use the launcher for a no-dependency download or Docker/local
development for the browser.

## What Delta does

- Generates outlines and editable cards from a prompt.
- Lets you edit, reorder, duplicate, and delete cards.
- Supports themes, layouts, images, charts, Mermaid diagrams, and icons.
- Imports text, PDF, DOCX, PPTX, and URLs.
- Exports PDF, PNG, PPTX, and standalone HTML.
- Saves decks locally with autosave, undo/redo, and version conflict safety.

## Troubleshooting

### The page does not open

- Launcher: wait a few seconds, then open the URL printed in the launcher log.
- Local development: confirm `make dev` is still running and open
  <http://127.0.0.1:5173>.
- Docker: confirm `docker compose ps` shows the `delta` service as running and
  open <http://localhost:8000>.

### OpenAI, Gemini, or Anthropic says the key is invalid

Check that the key belongs to the selected provider, that the model name is
available to your account, and that you have not pasted spaces before or after
the key. Provider usage and billing are controlled by that provider.

### Ollama is unavailable

Start Ollama and verify the model is installed:

```bash
ollama list
```

For Docker, use `docker compose ps` and
`docker compose exec ollama ollama list`.

### PDF or PNG export does not work

The first PDF/PNG export may need a Chrome/Edge browser or a Playwright
Chromium download. PPTX export is editable but intentionally text-oriented and
may not reproduce every visual detail.

## For contributors

```bash
uv sync --project backend
npm ci --prefix frontend
make check
```

`make check` runs Ruff, mypy, ESLint, Prettier, the backend tests, frontend
tests, and the frontend production build.

Useful commands:

```bash
make gen-api       # regenerate the typed frontend client
make benchmark     # benchmark configured models
make hooks-install # install pre-commit hooks
```

## Project structure

```text
backend/       FastAPI API, database, LLM providers, imports, exports
frontend/      React application and editor
launcher/      Browser launcher for packaged releases
desktop/       Tauri native shell
packaging/     PyInstaller bundle and smoke test
docs/          Download and desktop documentation
plan.md        Roadmap and implementation checklist
```

## License

Delta is licensed under the [GNU General Public License v3.0](LICENSE).
