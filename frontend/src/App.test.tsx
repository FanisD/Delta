import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { DeckDocument } from "./api"
import App from "./App"

const sampleDeck: DeckDocument = {
  id: "deck-one",
  title: "A story with a beginning",
  theme: "ocean",
  created_at: "2026-09-28T12:00:00Z",
  updated_at: "2026-09-28T12:00:00Z",
  cards: [
    {
      id: "card-one",
      title: "The opening",
      layout: "title",
      blocks: [
        { type: "heading", level: 1, text: "A clear idea" },
        { type: "paragraph", text: "A calm first card." },
        { type: "image", prompt: "A sunrise", alt: "A calm sunrise" },
      ],
    },
    {
      id: "card-two",
      title: "The details",
      layout: "two_column",
      blocks: [
        { type: "heading", text: "The details" },
        { type: "bullets", items: ["First point", "Second point"] },
        {
          type: "columns",
          columns: [
            { title: "Left", body: "A left-hand point." },
            { title: "Right", body: "A right-hand point." },
          ],
        },
        { type: "quote", text: "Keep it clear.", attribution: "A reminder" },
        { type: "stat", value: "2", label: "ideas" },
        {
          type: "table",
          headers: ["Signal", "Meaning"],
          rows: [["Clear", "Readable"]],
        },
        {
          type: "chart",
          title: "Example values",
          labels: ["One", "Two"],
          values: [10, 20],
          illustrative: true,
        },
      ],
    },
  ],
}

function stubApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const requestUrl = input instanceof Request ? input.url : input.toString()
    const { pathname } = new URL(requestUrl)
    if (pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    }
    if (pathname === "/api/decks") {
      return new Response(JSON.stringify([sampleDeck]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    }
    if (pathname === "/api/decks/deck-one") {
      return new Response(JSON.stringify({ ...sampleDeck, theme: "forest" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    }
    if (pathname === "/api/settings/providers") {
      return new Response(
        JSON.stringify({
          providers: [],
          defaults: { outline: null, content: null, edit: null },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      )
    }
    return new Response(null, { status: 404 })
  })
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("presentation library", () => {
  it("loads decks and reports backend health", async () => {
    stubApi()
    render(<App />)

    expect(await screen.findByText("Backend connected")).toBeInTheDocument()
    expect(
      await screen.findByRole("button", { name: /A story with a beginning/ }),
    ).toBeInTheDocument()
  })

  it("opens provider settings and returns to the library", async () => {
    stubApi()
    render(<App />)

    fireEvent.click(await screen.findByRole("button", { name: "Settings" }))
    expect(
      await screen.findByRole("heading", { name: "Model providers" }),
    ).toBeInTheDocument()
    fireEvent.click(
      screen.getByRole("button", { name: "Back to presentations" }),
    )
    expect(
      await screen.findByRole("heading", { name: "Your presentations" }),
    ).toBeInTheDocument()
  })

  it("renders block types, saves themes, and navigates with arrow keys", async () => {
    const fetchMock = stubApi()
    render(<App />)

    fireEvent.click(
      await screen.findByRole("button", { name: /A story with a beginning/ }),
    )
    expect(await screen.findByText("A calm first card.")).toBeInTheDocument()

    fireEvent.change(
      screen.getByRole("combobox", { name: "Presentation theme" }),
      {
        target: { value: "forest" },
      },
    )
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([request]) =>
            request instanceof Request && request.method === "PATCH",
        ),
      ).toBe(true)
    })

    fireEvent.click(screen.getByRole("button", { name: /Present/ }))
    expect(
      await screen.findByText("Use ← → to navigate · Esc to exit"),
    ).toBeInTheDocument()
    expect(screen.getByText("A calm sunrise")).toBeInTheDocument()
    fireEvent.keyDown(window, { key: "ArrowRight" })
    expect(await screen.findByText("Keep it clear.")).toBeInTheDocument()
    expect(screen.getByText("First point")).toBeInTheDocument()
    expect(screen.getByText("ideas")).toBeInTheDocument()
    expect(screen.getByRole("table")).toBeInTheDocument()
    expect(screen.getByText("Illustrative data")).toBeInTheDocument()
  })
})
