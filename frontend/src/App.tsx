import { useEffect, useState } from "react"
import { healthHealthGet } from "./api"
import { client } from "./api/client.gen"

client.setConfig({ baseUrl: window.location.origin })

type HealthState =
  | { status: "checking" }
  | { status: "connected" }
  | { status: "error"; message: string }

function App() {
  const [health, setHealth] = useState<HealthState>({ status: "checking" })

  useEffect(() => {
    let active = true

    healthHealthGet()
      .then(({ data, error, response }) => {
        if (!active) return

        if (data?.status === "ok") {
          setHealth({ status: "connected" })
          return
        }

        if (response) {
          setHealth({
            status: "error",
            message: `Backend returned HTTP ${response.status}`,
          })
          return
        }

        setHealth({
          status: "error",
          message:
            error instanceof Error
              ? error.message
              : "The health request failed",
        })
      })
      .catch((error: unknown) => {
        if (!active) return
        setHealth({
          status: "error",
          message:
            error instanceof Error
              ? error.message
              : "The health request failed",
        })
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-6 text-foreground">
      <section className="w-full max-w-xl space-y-6 rounded-xl border bg-card p-8 shadow-sm">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">
            Local-first AI presentation builder
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">
            Your workspace is ready
          </h1>
          <p className="text-muted-foreground">
            Create and edit presentations with the AI model you choose.
          </p>
        </div>
        <div aria-live="polite" role="status" className="text-sm">
          {health.status === "checking" && "Connecting to the backend…"}
          {health.status === "connected" && "Backend connected"}
          {health.status === "error" &&
            `Backend unavailable: ${health.message}`}
        </div>
      </section>
    </main>
  )
}

export default App
