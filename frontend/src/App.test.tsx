import { render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import App from "./App"

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("App", () => {
  it("reports when the backend health endpoint responds successfully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    )

    render(<App />)

    expect(await screen.findByText("Backend connected")).toBeInTheDocument()
  })
})
