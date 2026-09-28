import { useEffect, useMemo, useState } from "react"
import { ArrowLeft, Check, LoaderCircle, RefreshCw, Save } from "lucide-react"
import type {
  ModelDefaultsUpdate,
  OllamaModelsResponse,
  ProviderConfigUpdate,
  ProviderConfiguration,
  ProviderSettingsResponse,
} from "../../api"

type Provider = ProviderConfiguration["provider"]
type Role = "outline" | "content" | "edit"
type ProviderDraft = {
  model: string
  apiKey: string
  baseUrl: string
  clearApiKey: boolean
}
type Drafts = Record<Provider, ProviderDraft>
type ModelDefaultsDraft = Record<Role, string>

const roles: { id: Role; label: string }[] = [
  { id: "outline", label: "Outline" },
  { id: "content", label: "Card content" },
  { id: "edit", label: "Editing" },
]

const providerOptions: {
  id: Provider
  name: string
  modelPlaceholder: string
  needsKey: boolean
}[] = [
  {
    id: "gemini",
    name: "Google Gemini",
    modelPlaceholder: "gemini-2.5-flash",
    needsKey: true,
  },
  {
    id: "anthropic",
    name: "Anthropic Claude",
    modelPlaceholder: "claude-sonnet-4-5",
    needsKey: true,
  },
  {
    id: "xai",
    name: "xAI Grok",
    modelPlaceholder: "grok-3-mini",
    needsKey: true,
  },
  {
    id: "openai_compatible",
    name: "OpenAI-compatible",
    modelPlaceholder: "model-name",
    needsKey: false,
  },
  {
    id: "ollama",
    name: "Ollama",
    modelPlaceholder: "qwen2.5:7b",
    needsKey: false,
  },
]

const emptyDrafts: Drafts = {
  gemini: { model: "", apiKey: "", baseUrl: "", clearApiKey: false },
  anthropic: { model: "", apiKey: "", baseUrl: "", clearApiKey: false },
  xai: { model: "", apiKey: "", baseUrl: "", clearApiKey: false },
  openai_compatible: {
    model: "",
    apiKey: "",
    baseUrl: "",
    clearApiKey: false,
  },
  ollama: { model: "", apiKey: "", baseUrl: "", clearApiKey: false },
}

function isProvider(value: string): value is Provider {
  return providerOptions.some((item) => item.id === value)
}

function defaultSelection(
  settings: ProviderSettingsResponse | null,
  role: Role,
): string {
  const value = settings?.defaults[role]
  return value ? `${value.provider}::${value.model}` : ""
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${window.location.origin}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string
    } | null
    throw new Error(body?.detail ?? `Request failed (HTTP ${response.status}).`)
  }
  return (await response.json()) as T
}

function modelSelection(setting: string): ModelDefaultsUpdate[Role] {
  if (!setting) return null
  const separator = setting.indexOf("::")
  if (separator < 0) return null
  const provider = setting.slice(0, separator)
  if (!isProvider(provider)) return null
  return {
    provider,
    model: setting.slice(separator + 2),
  }
}

export function ProviderSettings({ onBack }: { onBack: () => void }) {
  const [settings, setSettings] = useState<ProviderSettingsResponse | null>(
    null,
  )
  const [drafts, setDrafts] = useState<Drafts>(emptyDrafts)
  const [defaultDraft, setDefaultDraft] = useState<ModelDefaultsDraft>({
    outline: "",
    content: "",
    edit: "",
  })
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [savingProvider, setSavingProvider] = useState<Provider | null>(null)
  const [savingDefaults, setSavingDefaults] = useState(false)
  const [busyOllama, setBusyOllama] = useState(false)
  const [notice, setNotice] = useState("")
  const [error, setError] = useState("")

  useEffect(() => {
    let active = true
    requestJson<ProviderSettingsResponse>("/api/settings/providers")
      .then((data) => {
        if (!active) return
        setSettings(data)
        setDefaultDraft({
          outline: defaultSelection(data, "outline"),
          content: defaultSelection(data, "content"),
          edit: defaultSelection(data, "edit"),
        })
        setDrafts((current) => {
          const next = { ...current }
          for (const provider of data.providers) {
            next[provider.provider] = {
              ...next[provider.provider],
              model: provider.model ?? "",
              baseUrl: provider.base_url ?? "",
            }
          }
          return next
        })
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Unable to load provider settings.",
          )
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const savedProviders = useMemo(
    () => new Map(settings?.providers.map((item) => [item.provider, item])),
    [settings],
  )

  const changeDraft = (
    provider: Provider,
    field: keyof ProviderDraft,
    value: string | boolean,
  ) => {
    setDrafts((current) => ({
      ...current,
      [provider]: { ...current[provider], [field]: value },
    }))
    setNotice("")
    setError("")
  }

  const saveProvider = async (provider: Provider, thenTest = false) => {
    const draft = drafts[provider]
    if (!draft.model.trim()) {
      setError("Enter a model name before saving this provider.")
      return
    }
    setSavingProvider(provider)
    setError("")
    setNotice("")
    const payload: ProviderConfigUpdate = {
      model: draft.model.trim(),
      base_url: draft.baseUrl.trim() || null,
      clear_api_key: draft.clearApiKey,
    }
    if (draft.apiKey) payload.api_key = draft.apiKey
    try {
      const saved = await requestJson<ProviderConfiguration>(
        `/api/settings/providers/${provider}`,
        { method: "PUT", body: JSON.stringify(payload) },
      )
      setSettings((current) => ({
        providers: [
          ...(current?.providers.filter((item) => item.provider !== provider) ??
            []),
          saved,
        ],
        defaults: current?.defaults ?? {
          outline: null,
          content: null,
          edit: null,
        },
      }))
      setDrafts((current) => ({
        ...current,
        [provider]: {
          ...current[provider],
          apiKey: "",
          clearApiKey: false,
        },
      }))
      if (thenTest) {
        const result = await requestJson<{ message: string }>(
          "/api/settings/providers/test",
          {
            method: "POST",
            body: JSON.stringify({ provider, model: draft.model.trim() }),
          },
        )
        setNotice(result.message)
      } else {
        setNotice(
          `${providerOptions.find((item) => item.id === provider)?.name} settings saved.`,
        )
      }
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to save provider settings.",
      )
    } finally {
      setSavingProvider(null)
    }
  }

  const saveDefaults = async () => {
    setSavingDefaults(true)
    setError("")
    setNotice("")
    const payload: ModelDefaultsUpdate = {
      outline: modelSelection(defaultDraft.outline),
      content: modelSelection(defaultDraft.content),
      edit: modelSelection(defaultDraft.edit),
    }
    try {
      const saved = await requestJson<ProviderSettingsResponse>(
        "/api/settings/models",
        { method: "PUT", body: JSON.stringify(payload) },
      )
      setSettings(saved)
      setNotice("Default models saved.")
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to save model defaults.",
      )
    } finally {
      setSavingDefaults(false)
    }
  }

  const discoverOllamaModels = async () => {
    setBusyOllama(true)
    setError("")
    try {
      const result = await requestJson<OllamaModelsResponse>(
        "/api/providers/ollama/models",
      )
      setOllamaModels(result.models.map((item) => item.name))
      setNotice(
        result.models.length
          ? `Found ${result.models.length} Ollama model${result.models.length === 1 ? "" : "s"}.`
          : "Ollama is running, but no models are installed yet.",
      )
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to reach Ollama.",
      )
    } finally {
      setBusyOllama(false)
    }
  }

  const configuredModels = (settings?.providers ?? []).filter(
    (provider) => provider.configured,
  )

  return (
    <section className="settings-page" aria-labelledby="settings-heading">
      <div className="settings-page__top">
        <button className="quiet-button" onClick={onBack}>
          <ArrowLeft size={17} />
          Back to presentations
        </button>
        <span className="eyebrow">LOCAL MODEL CONNECTIONS</span>
      </div>
      <div className="settings-page__intro">
        <h1 id="settings-heading">Model providers</h1>
        <p>
          Connect a hosted model or your local Ollama server. Provider keys are
          encrypted on this device and never shown again.
        </p>
      </div>

      {loading && (
        <p className="settings-message">Loading provider settings…</p>
      )}
      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="notice notice--success" role="status">
          {notice}
        </p>
      )}

      {!loading && (
        <>
          <div className="provider-grid">
            {providerOptions.map((option) => {
              const saved = savedProviders.get(option.id)
              const draft = drafts[option.id]
              const busy = savingProvider === option.id
              return (
                <article className="provider-panel" key={option.id}>
                  <div className="provider-panel__heading">
                    <div>
                      <span className="eyebrow">
                        {saved?.configured ? "CONFIGURED" : "OPTIONAL"}
                      </span>
                      <h2>{option.name}</h2>
                    </div>
                    {saved?.configured && (
                      <Check size={18} aria-label="Configured" />
                    )}
                  </div>
                  <label className="settings-field">
                    <span>Model</span>
                    <input
                      value={draft.model}
                      placeholder={option.modelPlaceholder}
                      onChange={(event) =>
                        changeDraft(option.id, "model", event.target.value)
                      }
                    />
                  </label>
                  {option.needsKey && (
                    <label className="settings-field">
                      <span>
                        API key{" "}
                        {saved?.api_key_configured && (
                          <small>(saved; leave blank to keep it)</small>
                        )}
                      </span>
                      <input
                        type="password"
                        autoComplete="new-password"
                        value={draft.apiKey}
                        placeholder={
                          saved?.api_key_configured
                            ? "Saved securely"
                            : "Paste API key"
                        }
                        onChange={(event) => {
                          changeDraft(option.id, "apiKey", event.target.value)
                          if (event.target.value) {
                            changeDraft(option.id, "clearApiKey", false)
                          }
                        }}
                      />
                      {saved?.api_key_configured && (
                        <label className="settings-checkbox">
                          <input
                            type="checkbox"
                            checked={draft.clearApiKey}
                            onChange={(event) =>
                              changeDraft(
                                option.id,
                                "clearApiKey",
                                event.target.checked,
                              )
                            }
                          />
                          Remove saved API key
                        </label>
                      )}
                    </label>
                  )}
                  {(option.id === "openai_compatible" ||
                    option.id === "ollama") && (
                    <label className="settings-field">
                      <span>
                        Base URL {option.id === "ollama" && "(optional)"}
                      </span>
                      <input
                        type="url"
                        value={draft.baseUrl}
                        placeholder={
                          option.id === "ollama"
                            ? "http://localhost:11434"
                            : "https://your-endpoint/v1"
                        }
                        onChange={(event) =>
                          changeDraft(option.id, "baseUrl", event.target.value)
                        }
                      />
                    </label>
                  )}
                  {option.id === "ollama" && (
                    <div className="ollama-models">
                      <button
                        className="text-button"
                        disabled={busyOllama}
                        onClick={() => void discoverOllamaModels()}
                      >
                        {busyOllama ? (
                          <LoaderCircle size={14} className="spin" />
                        ) : (
                          <RefreshCw size={14} />
                        )}
                        Find installed models
                      </button>
                      {ollamaModels.length > 0 && (
                        <div className="ollama-models__list">
                          {ollamaModels.map((model) => (
                            <button
                              key={model}
                              className="text-button"
                              onClick={() =>
                                changeDraft("ollama", "model", model)
                              }
                            >
                              {model}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="provider-panel__actions">
                    <button
                      className="quiet-button"
                      disabled={busy || !saved?.configured}
                      onClick={() => void saveProvider(option.id, true)}
                    >
                      Test connection
                    </button>
                    <button
                      className="primary-button"
                      disabled={busy}
                      onClick={() => void saveProvider(option.id)}
                    >
                      {busy ? (
                        <LoaderCircle size={15} className="spin" />
                      ) : (
                        <Save size={15} />
                      )}
                      Save
                    </button>
                  </div>
                </article>
              )
            })}
          </div>

          <section
            className="model-defaults"
            aria-labelledby="defaults-heading"
          >
            <div>
              <span className="eyebrow">MODEL ROUTING</span>
              <h2 id="defaults-heading">Default model by role</h2>
              <p>
                Choose which configured model Delta should use for each job.
              </p>
            </div>
            <div className="model-defaults__grid">
              {roles.map((role) => (
                <label className="settings-field" key={role.id}>
                  <span>{role.label}</span>
                  <select
                    value={defaultDraft[role.id]}
                    onChange={(event) =>
                      setDefaultDraft((current) => ({
                        ...current,
                        [role.id]: event.target.value,
                      }))
                    }
                  >
                    <option value="">Not selected</option>
                    {configuredModels.map((provider) => {
                      const savedDefault = settings?.defaults[role.id]
                      const models = new Set([
                        provider.model,
                        savedDefault?.provider === provider.provider
                          ? savedDefault.model
                          : "",
                      ])
                      return [...models]
                        .filter((model): model is string => Boolean(model))
                        .map((model) => (
                          <option
                            key={`${provider.provider}::${model}`}
                            value={`${provider.provider}::${model}`}
                          >
                            {
                              providerOptions.find(
                                (item) => item.id === provider.provider,
                              )?.name
                            }{" "}
                            · {model}
                          </option>
                        ))
                    })}
                  </select>
                </label>
              ))}
            </div>
            <button
              className="primary-button"
              disabled={savingDefaults || configuredModels.length === 0}
              onClick={() => void saveDefaults()}
            >
              {savingDefaults ? (
                <LoaderCircle size={15} className="spin" />
              ) : (
                <Save size={15} />
              )}
              Save defaults
            </button>
          </section>
        </>
      )}
    </section>
  )
}
