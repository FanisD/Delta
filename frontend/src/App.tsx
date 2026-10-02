import { useEffect, useMemo, useState } from "react"
import {
  ArrowLeft,
  ArrowRight,
  Expand,
  LayoutGrid,
  Maximize2,
  Play,
  Presentation,
  Settings as SettingsIcon,
} from "lucide-react"
import {
  healthHealthGet,
  listDecksApiDecksGet,
  updateDeckApiDecksDeckIdPatch,
  type DeckDocument,
  type Theme,
} from "./api"
import { client } from "./api/client.gen"
import { DeckCard } from "./components/decks/DeckCard"
import { ProviderSettings } from "./components/settings/ProviderSettings"
import { GenerationPanel } from "./components/generation/GenerationPanel"

client.setConfig({ baseUrl: window.location.origin })

type LoadState = "loading" | "ready" | "error"
const themes: { id: Theme; label: string }[] = [
  { id: "ocean", label: "Ocean" },
  { id: "sunset", label: "Sunset" },
  { id: "forest", label: "Forest" },
]

function isTheme(value: string): value is Theme {
  return themes.some((theme) => theme.id === value)
}

function App() {
  const [decks, setDecks] = useState<DeckDocument[]>([])
  const [loadState, setLoadState] = useState<LoadState>("loading")
  const [loadError, setLoadError] = useState("")
  const [backendStatus, setBackendStatus] = useState("Checking backend…")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [presenting, setPresenting] = useState(false)
  const [slideIndex, setSlideIndex] = useState(0)
  const [savingTheme, setSavingTheme] = useState(false)
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [showSettings, setShowSettings] = useState(false)
  const [showGenerator, setShowGenerator] = useState(false)

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

  const changeTheme = async (theme: Theme) => {
    if (!selectedDeck || selectedDeck.theme === theme || savingTheme) return
    setSavingTheme(true)
    const { data, error } = await updateDeckApiDecksDeckIdPatch({
      path: { deck_id: selectedDeck.id },
      body: { theme },
    })
    setSavingTheme(false)

    if (error || !data) {
      setLoadError("The theme could not be saved. Please try again.")
      return
    }

    setDecks((current) =>
      current.map((deck) => (deck.id === data.id ? data : deck)),
    )
    setLoadError("")
  }

  const startPresentation = async () => {
    if (!selectedDeck) return
    setSlideIndex(0)
    setPresenting(true)
    try {
      await document.documentElement.requestFullscreen?.()
    } catch {
      setLoadError(
        "Fullscreen is unavailable; presentation mode will continue in this tab.",
      )
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
        <section className="deck-workspace">
          <div className="workspace-heading">
            <button
              className="quiet-button"
              onClick={() => setSelectedId(null)}
            >
              <ArrowLeft size={17} />
              All presentations
            </button>
            <div className="workspace-heading__actions">
              <label className="theme-picker">
                <span>Theme</span>
                <select
                  aria-label="Presentation theme"
                  value={selectedDeck.theme}
                  disabled={savingTheme}
                  onChange={(event) => {
                    if (isTheme(event.target.value)) {
                      void changeTheme(event.target.value)
                    }
                  }}
                >
                  {themes.map((theme) => (
                    <option key={theme.id} value={theme.id}>
                      {theme.label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="primary-button"
                onClick={() => void startPresentation()}
              >
                <Play size={16} fill="currentColor" />
                Present
              </button>
            </div>
          </div>

          {loadError && <p className="notice notice--error">{loadError}</p>}
          <div className="deck-title-block">
            <span className="eyebrow">
              PRESENTATION · {selectedDeck.cards.length} CARDS
            </span>
            <h1>{selectedDeck.title}</h1>
            <p>Scroll to explore, or present one card at a time.</p>
          </div>
          <div className="deck-scroll">
            {selectedDeck.cards.map((card, index) => (
              <DeckCard
                card={card}
                index={index}
                total={selectedDeck.cards.length}
                key={card.id ?? index}
              />
            ))}
          </div>
        </section>
      ) : (
        <section id="home" className="library">
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
              {decks.map((deck, index) => (
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
        <span>Thoughtfully made, locally.</span>
      </footer>
    </main>
  )
}

export default App
