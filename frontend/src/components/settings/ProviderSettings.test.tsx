import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { ProviderSettings } from "./ProviderSettings"

const emptySettings = {
  providers: [],
  defaults: { outline: null, content: null, edit: null },
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe("provider settings", () => {
  it("saves credentials without echoing them and assigns a default model", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString()
        const method = init?.method ?? "GET"
        if (url.endsWith("/api/settings/providers") && method === "GET") {
          return Response.json(emptySettings)
        }
        if (
          url.endsWith("/api/settings/providers/gemini") &&
          method === "PUT"
        ) {
          return Response.json({
            provider: "gemini",
            configured: true,
            model: "gemini-2.5-flash",
            base_url: null,
            api_key_configured: true,
          })
        }
        if (url.endsWith("/api/settings/models") && method === "PUT") {
          const body = JSON.parse(String(init?.body)) as {
            outline: { provider: string; model: string } | null
          }
          return Response.json({
            providers: [
              {
                provider: "gemini",
                configured: true,
                model: "gemini-2.5-flash",
                base_url: null,
                api_key_configured: true,
              },
            ],
            defaults: {
              outline: body.outline,
              content: null,
              edit: null,
            },
          })
        }
        return Response.json(
          { detail: "Unexpected API request." },
          { status: 404 },
        )
      },
    )
    vi.stubGlobal("fetch", fetchMock)
    render(<ProviderSettings onBack={vi.fn()} />)

    const modelInputs = await screen.findAllByLabelText("Model")
    fireEvent.change(modelInputs[0], { target: { value: "gemini-2.5-flash" } })
    const keyInput = screen.getAllByLabelText(/API key/)[0]
    fireEvent.change(keyInput, { target: { value: "test-secret-key" } })
    fireEvent.click(screen.getAllByRole("button", { name: /^Save$/ })[0])

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings/providers/gemini"),
        expect.objectContaining({
          method: "PUT",
          body: expect.stringContaining('"api_key":"test-secret-key"'),
        }),
      )
    })
    expect(
      await screen.findByText("Google Gemini settings saved."),
    ).toBeInTheDocument()
    expect(document.body).not.toHaveTextContent("test-secret-key")

    fireEvent.change(screen.getByLabelText("Outline"), {
      target: { value: "gemini::gemini-2.5-flash" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Save defaults" }))
    expect(await screen.findByText("Default models saved.")).toBeInTheDocument()

    const defaultsCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        url.toString().endsWith("/api/settings/models") &&
        init?.method === "PUT",
    )
    expect(defaultsCall?.[1]?.body).toContain(
      '"outline":{"provider":"gemini","model":"gemini-2.5-flash"}',
    )
  })
})
