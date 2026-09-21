import { useEffect, useState } from "react"
import type { FormEvent } from "react"

import { apiFetch, readError } from "../api/client"

type StatusPageConfig = {
  title: string
  subtitle: string
  support_url: string
  updated_at: string
}

const EMPTY_CONFIG = {
  title: "",
  subtitle: "",
  support_url: "",
}

export function StatusPageConfigForm() {
  const [form, setForm] = useState(EMPTY_CONFIG)
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const response = await apiFetch("/api/status/config/")
        if (!response.ok) {
          throw new Error(await readError(response, "Failed to load status config"))
        }
        const payload: StatusPageConfig = await response.json()
        if (!cancelled) {
          setForm({
            title: payload.title ?? "",
            subtitle: payload.subtitle ?? "",
            support_url: payload.support_url ?? "",
          })
          setUpdatedAt(payload.updated_at ?? null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const response = await apiFetch("/api/status/config/", {
        method: "PATCH",
        json: form,
      })
      if (!response.ok) {
        throw new Error(await readError(response, "Failed to save status config"))
      }
      const payload: StatusPageConfig = await response.json()
      setForm({
        title: payload.title ?? "",
        subtitle: payload.subtitle ?? "",
        support_url: payload.support_url ?? "",
      })
      setUpdatedAt(payload.updated_at ?? null)
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error")
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="app__form-section">
      <h2>Status page branding</h2>
      {loading && <p>Loading…</p>}
      {error && <p className="app__error">{error}</p>}
      {!loading && (
        <form className="endpoint-form" onSubmit={(event) => void handleSubmit(event)}>
          <div className="endpoint-form__grid">
            <label className="endpoint-form__wide">
              Title
              <input
                value={form.title}
                onChange={(event) => {
                  setSaved(false)
                  setForm({ ...form, title: event.target.value })
                }}
                placeholder="Apollo Status"
              />
            </label>
            <label className="endpoint-form__wide">
              Subtitle
              <input
                value={form.subtitle}
                onChange={(event) => {
                  setSaved(false)
                  setForm({ ...form, subtitle: event.target.value })
                }}
                placeholder="Live health for public endpoints"
              />
            </label>
            <label className="endpoint-form__wide">
              Support URL
              <input
                type="url"
                value={form.support_url}
                onChange={(event) => {
                  setSaved(false)
                  setForm({ ...form, support_url: event.target.value })
                }}
                placeholder="https://example.com/support"
              />
            </label>
          </div>
          <div className="endpoint-form__actions">
            <button type="submit" className="app__button" disabled={saving}>
              {saving ? "Saving…" : "Save branding"}
            </button>
            {saved && <span className="app__muted">Saved</span>}
            {updatedAt && (
              <span className="app__muted">
                Last updated {new Date(updatedAt).toLocaleString()}
              </span>
            )}
          </div>
        </form>
      )}
    </section>
  )
}
