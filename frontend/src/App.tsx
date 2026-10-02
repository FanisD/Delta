import { useEffect, useMemo, useState } from "react"
import {
  ArrowLeft,
  ArrowRight,
  Expand,
  LayoutGrid,
  Maximize2,
  Presentation,
  Settings as SettingsIcon,
} from "lucide-react"
import {
  healthHealthGet,
  listDecksApiDecksGet,
  deleteDeckApiDecksDeckIdDelete,
  type DeckDocument,
  type Theme,
} from "./api"
import { client } from "./api/client.gen"
import { DeckCard } from "./components/decks/DeckCard"
import { ProviderSettings } from "./components/settings/ProviderSettings"
import { GenerationPanel } from "./components/generation/GenerationPanel"
import { DeckEditor } from "./components/decks/DeckEditor"
import { PrintDeck } from "./components/decks/PrintDeck"

client.setConfig({ baseUrl: window.location.origin })

type LoadState = "loading" | "ready" | "error"
const themes: { id: Theme; label: string }[] = [
  { id: "ocean", label: "Ocean" },
  { id: "sunset", label: "Sunset" },
  { id: "forest", label: "Forest" },
]

function MainApp() {
  const [decks, setDecks] = useState<DeckDocument[]>([])
  const [loadState, setLoadState] = useState<LoadState>("loading")
  const [loadError, setLoadError] = useState("")
  const [backendStatus, setBackendStatus] = useState("Checking backend…")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [presenting, setPresenting] = useState(false)
  const [slideIndex, setSlideIndex] = useState(0)
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [showSettings, setShowSettings] = useState(false)
  const [showGenerator, setShowGenerator] = useState(false)
  const [search, setSearch] = useState("")
  const [appInfo, setAppInfo] = useState<{
    version: string
    data_directory: string
  } | null>(null)
  const [update, setUpdate] = useState<{
    available: boolean
    latest_version?: string | null
    release_url?: string | null
  } | null>(null)
  const [showWelcome, setShowWelcome] = useState(
    () => window.localStorage.getItem("delta.welcome.dismissed") !== "1",
  )
  const [updatesEnabled, setUpdatesEnabled] = useState(
    () => window.localStorage.getItem("delta.updates.disabled") !== "1",
  )
  const [ollamaStatus, setOllamaStatus] = useState<
    "checking" | "available" | "offline"
  >("checking")
  const [ollamaModelCount, setOllamaModelCount] = useState(0)

  const selectedDeck = useMemo(
    () => decks.find((deck) => deck.id === selectedId) ?? null,
    [decks, selectedId],
  )

  useEffect(() => {
    let active = true
    Promise.all([healthHealthGet(), listDecksApiDecksGet()])
      .then(
        ([{ data: health, error: healthError }, { data, error, response }]) => {
          if (!active) return
          setBackendStatus(
            health?.status === "ok"
              ? "Backend connected"
              : healthError
                ? "Backend unavailable"
                : "Backend returned an invalid status",
          )
          if (error || !data) {
            setLoadError(
              response
                ? `Unable to load presentations (HTTP ${response.status}).`
                : "Unable to reach the backend. Check that `make dev` is running.",
            )
            setLoadState("error")
            return
          }
          setDecks(data)
          setLoadError("")
          setLoadState("ready")
        },
      )
      .catch(() => {
        if (!active) return
        setBackendStatus("Backend unavailable")
        setLoadError(
          "Unable to reach the backend. Check that `make dev` is running.",
        )
        setLoadState("error")
      })
    return () => {
      active = false
    }
  }, [loadAttempt])

  useEffect(() => {
    fetch("/api/settings/app")
      .then((response) => (response.ok ? response.json() : null))
      .then((info) => info && setAppInfo(info))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!updatesEnabled) return
    fetch("/api/updates/check")
      .then((response) => (response.ok ? response.json() : null))
      .then((result) => result?.available && setUpdate(result))
      .catch(() => undefined)
  }, [updatesEnabled])

  useEffect(() => {
    fetch("/api/providers/ollama/models")
      .then(async (response) => {
        if (!response.ok) throw new Error("offline")
        const payload = (await response.json()) as { models?: unknown[] }
        setOllamaModelCount(payload.models?.length ?? 0)
        setOllamaStatus("available")
      })
      .catch(() => setOllamaStatus("offline"))
  }, [])

  useEffect(() => {
    if (!presenting || !selectedDeck) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault()
        setSlideIndex((index) =>
          Math.min(index + 1, selectedDeck.cards.length - 1),
        )
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault()
        setSlideIndex((index) => Math.max(index - 1, 0))
      } else if (event.key === "Home") {
        setSlideIndex(0)
      } else if (event.key === "End") {
        setSlideIndex(selectedDeck.cards.length - 1)
      } else if (event.key === "Escape") {
        setPresenting(false)
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [presenting, selectedDeck])

  const openDeck = (deckId: string) => {
    setSlideIndex(0)
    setSelectedId(deckId)
    setPresenting(false)
  }

  const removeDeck = async (deckId: string) => {
    if (!window.confirm("Delete this presentation?")) return
    const { error } = await deleteDeckApiDecksDeckIdDelete({
      path: { deck_id: deckId },
    })
    if (!error) setDecks((items) => items.filter((item) => item.id !== deckId))
  }

  const duplicateDeck = async (deckId: string) => {
    const response = await fetch(`/api/decks/${deckId}/duplicate`, {
      method: "POST",
    })
    if (response.ok) {
      const copy = await response.json()
      setDecks((items) => [copy, ...items])
    }
  }

  const exitPresentation = async () => {
    setPresenting(false)
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    }
  }

  if (presenting && selectedDeck) {
    const card = selectedDeck.cards[slideIndex]
    return (
      <main className="presentation-screen" data-theme={selectedDeck.theme}>
        <header className="presentation-toolbar">
          <button
            className="quiet-button"
            onClick={() => void exitPresentation()}
          >
            <ArrowLeft size={17} />
            Exit presentation
          </button>
          <span>{selectedDeck.title}</span>
          <span className="presentation-toolbar__hint">
            Use ← → to navigate · Esc to exit
          </span>
        </header>
        {card && (
          <DeckCard
            card={card}
            index={slideIndex}
            total={selectedDeck.cards.length}
            presentation
          />
        )}
        <nav
          className="presentation-controls"
          aria-label="Presentation navigation"
        >
          <button
            className="quiet-button"
            aria-label="Previous card"
            disabled={slideIndex === 0}
            onClick={() => setSlideIndex((index) => Math.max(index - 1, 0))}
          >
            <ArrowLeft size={18} />
            Previous
          </button>
          <span>
            {slideIndex + 1} / {selectedDeck.cards.length}
          </span>
          <button
            className="quiet-button"
            aria-label="Next card"
            disabled={slideIndex === selectedDeck.cards.length - 1}
            onClick={() =>
              setSlideIndex((index) =>
                Math.min(index + 1, selectedDeck.cards.length - 1),
              )
            }
          >
            Next
            <ArrowRight size={18} />
          </button>
        </nav>
      </main>
    )
  }

  return (
    <main
      className="presentation-app"
      data-theme={selectedDeck?.theme ?? "ocean"}
    >
      <header className="app-header">
        <a
          className="brand"
          href="#home"
          onClick={(event) => {
            event.preventDefault()
            setSelectedId(null)
            setPresenting(false)
            setShowSettings(false)
            setShowGenerator(false)
          }}
          aria-label="Delta home"
        >
          <span className="brand-mark">
            <Presentation size={19} />
          </span>
          <span>delta</span>
        </a>
        <div className="app-header__status">
          <span
            className={
              backendStatus === "Backend connected"
                ? "status-dot"
                : "status-dot status-dot--quiet"
            }
          />
          {backendStatus}
        </div>
        <button
          className="quiet-button settings-nav"
          onClick={() => {
            setSelectedId(null)
            setShowSettings(true)
          }}
        >
          <SettingsIcon size={15} />
          Settings
        </button>
      </header>

      {showSettings ? (
        <ProviderSettings onBack={() => setShowSettings(false)} />
      ) : showGenerator ? (
        <GenerationPanel
          onDone={() => {
            setShowGenerator(false)
            setLoadAttempt((attempt) => attempt + 1)
          }}
        />
      ) : selectedDeck ? (
        <DeckEditor
          deck={selectedDeck}
          onChange={(deck) =>
            setDecks((items) =>
              items.map((item) => (item.id === deck.id ? deck : item)),
            )
          }
          onBack={() => setSelectedId(null)}
          onPresent={() => setPresenting(true)}
        />
      ) : (
        <section id="home" className="library">
          {showWelcome && (
            <aside className="welcome-card" role="status">
              <div>
                <span className="eyebrow">WELCOME TO DELTA</span>
                <h2>Start locally, keep control.</h2>
                <p>
                  Use Ollama for local models, or open Settings to add an API
                  provider. Your presentations stay in{" "}
                  <code>
                    {appInfo?.data_directory ?? "your app data folder"}
                  </code>
                  .
                </p>
                <p className="welcome-card__hint">
                  Ollama status:{" "}
                  <strong>
                    {ollamaStatus === "checking"
                      ? "checking…"
                      : ollamaStatus === "available"
                        ? `running (${ollamaModelCount} model${ollamaModelCount === 1 ? "" : "s"})`
                        : "not running"}
                  </strong>
                  . Install it from{" "}
                  <a href="https://ollama.com" target="_blank" rel="noreferrer">
                    ollama.com
                  </a>{" "}
                  and pull a model such as <code>ollama pull qwen2.5:7b</code>.
                </p>
              </div>
              <button
                className="quiet-button"
                onClick={() => {
                  window.localStorage.setItem("delta.welcome.dismissed", "1")
                  setShowWelcome(false)
                }}
              >
                Got it
              </button>
            </aside>
          )}
          {update?.available && update.release_url && (
            <aside className="update-banner" role="status">
              <span>
                Delta {update.latest_version} is available.
                <a href={update.release_url} target="_blank" rel="noreferrer">
                  {" "}
                  Download it from Releases.
                </a>
              </span>
              <button
                className="text-button"
                onClick={() => setUpdate(null)}
                aria-label="Dismiss update notice"
              >
                Dismiss
              </button>
            </aside>
          )}
          <div className="library-hero">
            <div className="library-hero__copy">
              <span className="eyebrow">YOUR IDEAS, BEAUTIFULLY ARRANGED</span>
              <h1>
                Make room for
                <br />a <em>great story.</em>
              </h1>
              <p>Thoughtful presentations, shaped around the way you think.</p>
            </div>
            <div className="library-hero__art" aria-hidden="true">
              <div className="art-card art-card--back" />
              <div className="art-card art-card--middle" />
              <div className="art-card art-card--front">
                <span>01 — THE BIG IDEA</span>
                <strong>
                  Clarity creates
                  <br />
                  momentum.
                </strong>
                <i />
              </div>
              <div className="art-spark art-spark--one">✳</div>
              <div className="art-spark art-spark--two">✳</div>
            </div>
          </div>

          <div className="library-heading">
            <div>
              <span className="eyebrow">A FEW IDEAS TO GET YOU STARTED</span>
              <h2>Your presentations</h2>
            </div>
            <input
              className="library-search"
              placeholder="Search presentations…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search presentations"
            />
            <button
              className="primary-button"
              onClick={() => setShowGenerator(true)}
            >
              Create with AI
            </button>
            <span className="library-heading__count">
              <LayoutGrid size={15} />
              {decks.length} {decks.length === 1 ? "story" : "stories"}
            </span>
          </div>

          {loadState === "loading" && (
            <p className="library-message">Gathering your presentations…</p>
          )}
          {loadState === "error" && (
            <div className="notice notice--error" role="alert">
              <span>{loadError}</span>
              <button
                className="text-button"
                onClick={() => {
                  setLoadState("loading")
                  setLoadAttempt((attempt) => attempt + 1)
                }}
              >
                Try again
              </button>
            </div>
          )}
          {loadState === "ready" && decks.length === 0 && (
            <p className="library-message">
              No presentations yet. Your first story will appear here.
            </p>
          )}
          {loadState === "ready" && decks.length > 0 && (
            <div className="deck-grid">
              {decks
                .filter((deck) =>
                  deck.title.toLowerCase().includes(search.toLowerCase()),
                )
                .map((deck, index) => (
                  <button
                    className="deck-tile"
                    data-theme={deck.theme}
                    key={deck.id}
                    onClick={() => openDeck(deck.id)}
                  >
                    <span
                      className={`deck-tile__preview deck-tile__preview--${index % 3}`}
                    >
                      <span className="deck-tile__preview-label">
                        A DELTA PRESENTATION
                      </span>
                      <strong>{deck.title}</strong>
                      <span className="deck-tile__preview-lines">
                        <i />
                        <i />
                        <i />
                      </span>
                      <span className="deck-tile__preview-mark">
                        <Expand size={17} />
                      </span>
                    </span>
                    <span className="deck-tile__details">
                      <span>
                        <strong>{deck.title}</strong>
                        <small>
                          {deck.cards.length} cards ·{" "}
                          {themes.find((theme) => theme.id === deck.theme)
                            ?.label ?? "Ocean"}{" "}
                          theme
                        </small>
                      </span>
                      <Maximize2 size={16} />
                    </span>
                    <span className="deck-tile__actions">
                      <button
                        className="quiet-button"
                        onClick={(event) => {
                          event.stopPropagation()
                          void duplicateDeck(deck.id)
                        }}
                      >
                        Duplicate
                      </button>
                      <button
                        className="quiet-button"
                        onClick={(event) => {
                          event.stopPropagation()
                          void removeDeck(deck.id)
                        }}
                      >
                        Delete
                      </button>
                    </span>
                  </button>
                ))}
            </div>
          )}
        </section>
      )}

      <footer className="app-footer">
        <span>
          Delta <span aria-hidden="true">·</span> Your ideas stay yours.
        </span>
        <span>
          Thoughtfully made, locally.{" "}
          <label className="update-setting">
            <input
              type="checkbox"
              checked={updatesEnabled}
              onChange={(event) => {
                const enabled = event.target.checked
                setUpdatesEnabled(enabled)
                window.localStorage.setItem(
                  "delta.updates.disabled",
                  enabled ? "0" : "1",
                )
              }}
            />
            Check for updates
          </label>
        </span>
      </footer>
    </main>
  )
}

function App() {
  const printMatch = window.location.pathname.match(/^\/print\/([^/]+)\/?$/)
  if (printMatch) {
    return <PrintDeck deckId={decodeURIComponent(printMatch[1])} />
  }
  return <MainApp />
}

export default App
