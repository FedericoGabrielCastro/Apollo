import { useEffect } from "react"

import { useAppDispatch, useAppSelector } from "./store/hooks"
import { checkEndpoint, fetchEndpoints } from "./store/endpointsSlice"
import { fetchHealth } from "./store/healthSlice"
import "./App.css"

function statusLabel(status: string | undefined) {
  if (!status) return "never checked"
  return status
}

function App() {
  const dispatch = useAppDispatch()
  const health = useAppSelector((state) => state.health)
  const endpoints = useAppSelector((state) => state.endpoints)

  useEffect(() => {
    void dispatch(fetchHealth())
    void dispatch(fetchEndpoints())
  }, [dispatch])

  return (
    <main className="app">
      <header className="app__header">
        <p className="app__brand">Apollo</p>
        <h1>API Health Monitor</h1>
        <p className="app__lede">
          Probe monitored endpoints and watch their latest status.
        </p>
      </header>

      <section className="app__status" aria-live="polite">
        <h2>Backend</h2>
        {health.loading && <p>Checking…</p>}
        {health.error && <p className="app__error">{health.error}</p>}
        {health.data && (
          <p className="app__pill app__pill--up">
            {health.data.service}: {health.data.status}
          </p>
        )}
      </section>

      <section className="app__endpoints">
        <div className="app__endpoints-head">
          <h2>Endpoints</h2>
          <button
            type="button"
            className="app__button"
            onClick={() => void dispatch(fetchEndpoints())}
            disabled={endpoints.loading}
          >
            Refresh
          </button>
        </div>

        {endpoints.loading && endpoints.items.length === 0 && <p>Loading…</p>}
        {endpoints.error && <p className="app__error">{endpoints.error}</p>}
        {!endpoints.loading && endpoints.items.length === 0 && (
          <p>No endpoints yet. Run `poetry run python manage.py seed`.</p>
        )}

        <ul className="app__list">
          {endpoints.items.map((endpoint) => {
            const last = endpoint.last_check
            const pillClass = last
              ? `app__pill app__pill--${last.status}`
              : "app__pill"
            const checking = endpoints.checkingId === endpoint.id

            return (
              <li key={endpoint.id} className="app__row">
                <div>
                  <p className="app__row-name">{endpoint.name}</p>
                  <p className="app__row-url">
                    {endpoint.method} {endpoint.url}
                  </p>
                  <p className={pillClass}>
                    {statusLabel(last?.status)}
                    {last?.latency_ms != null ? ` · ${last.latency_ms}ms` : ""}
                    {last?.status_code != null ? ` · HTTP ${last.status_code}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  className="app__button"
                  disabled={checking || !endpoint.is_active}
                  onClick={() => void dispatch(checkEndpoint(endpoint.id))}
                >
                  {checking ? "Checking…" : "Check now"}
                </button>
              </li>
            )
          })}
        </ul>
      </section>
    </main>
  )
}

export default App
