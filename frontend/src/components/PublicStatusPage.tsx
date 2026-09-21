import { useEffect, useState } from "react"
import { Link } from "react-router-dom"

import { apiFetch, readError } from "../api/client"

type PublicEndpoint = {
  name: string
  status: string
  latency_ms: number | null
  last_checked_at: string | null
  tags: string[]
}

type PublicIncident = {
  endpoint_name: string
  summary: string
  opened_at: string
}

type PublicStatus = {
  service: string
  overall: "unknown" | "operational" | "degraded" | "major_outage"
  generated_at: string
  endpoints: PublicEndpoint[]
  active_incidents: PublicIncident[]
}

function overallLabel(overall: PublicStatus["overall"]) {
  switch (overall) {
    case "operational":
      return "All systems operational"
    case "degraded":
      return "Degraded performance"
    case "major_outage":
      return "Major outage"
    default:
      return "Status unknown"
  }
}

function overallPillClass(overall: PublicStatus["overall"]) {
  switch (overall) {
    case "operational":
      return "app__pill app__pill--up"
    case "degraded":
      return "app__pill app__pill--error"
    case "major_outage":
      return "app__pill app__pill--down"
    default:
      return "app__pill"
  }
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

export function PublicStatusPage() {
  const [data, setData] = useState<PublicStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const response = await apiFetch("/api/status/public/", { auth: false })
        if (!response.ok) {
          throw new Error(await readError(response, "Failed to load status"))
        }
        const payload: PublicStatus = await response.json()
        if (!cancelled) {
          setData(payload)
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

  return (
    <main className="app status-page">
      <header className="app__header">
        <div className="app__header-top">
          <p className="app__brand">Apollo</p>
          <nav className="status-page__nav">
            <Link to="/" className="status-page__link">
              Monitor
            </Link>
            <Link to="/login" className="status-page__link">
              Sign in
            </Link>
          </nav>
        </div>
        <h1>Public status</h1>
        <p className="app__lede">
          Live health for publicly listed endpoints. No authentication required.
        </p>
      </header>

      {loading && <p>Loading status…</p>}
      {error && <p className="app__error">{error}</p>}

      {data && (
        <>
          <section className="status-page__overall" aria-live="polite">
            <h2>Overall</h2>
            <p className={overallPillClass(data.overall)}>{overallLabel(data.overall)}</p>
            <p className="status-page__meta">
              Updated {formatTime(data.generated_at)} · {data.service}
            </p>
          </section>

          {data.active_incidents.length > 0 && (
            <section className="status-page__incidents">
              <h2>Active incidents</h2>
              <ul className="status-page__list">
                {data.active_incidents.map((incident) => (
                  <li key={`${incident.endpoint_name}-${incident.opened_at}`}>
                    <strong>{incident.endpoint_name}</strong>
                    <span className="app__badge app__badge--incident">open</span>
                    <p className="status-page__summary">{incident.summary}</p>
                    <p className="status-page__meta">Opened {formatTime(incident.opened_at)}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="status-page__endpoints">
            <h2>Endpoints</h2>
            {data.endpoints.length === 0 ? (
              <p className="check-history__empty">No public endpoints configured.</p>
            ) : (
              <ul className="status-page__list">
                {data.endpoints.map((endpoint) => (
                  <li key={endpoint.name}>
                    <div className="status-page__endpoint-head">
                      <span className="app__row-name">{endpoint.name}</span>
                      <span
                        className={
                          endpoint.status === "up"
                            ? "app__pill app__pill--up"
                            : endpoint.status === "down" || endpoint.status === "error"
                              ? "app__pill app__pill--down"
                              : "app__pill"
                        }
                      >
                        {endpoint.status}
                        {endpoint.latency_ms != null ? ` · ${endpoint.latency_ms}ms` : ""}
                      </span>
                    </div>
                    {endpoint.tags.length > 0 && (
                      <div className="app__tags">
                        {endpoint.tags.map((tag) => (
                          <span key={tag} className="app__tag">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    {endpoint.last_checked_at && (
                      <p className="status-page__meta">
                        Last checked {formatTime(endpoint.last_checked_at)}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </main>
  )
}
