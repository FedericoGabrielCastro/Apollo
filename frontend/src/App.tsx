import { useEffect, useState } from "react"

import { CheckHistory } from "./components/CheckHistory"
import { EndpointForm } from "./components/EndpointForm"
import { useAppDispatch, useAppSelector } from "./store/hooks"
import {
  checkDueEndpoints,
  checkEndpoint,
  createEndpoint,
  deleteEndpoint,
  fetchEndpointHistory,
  fetchEndpoints,
  updateEndpoint,
  type EndpointInput,
  type MonitoredEndpoint,
} from "./store/endpointsSlice"
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
  const [editing, setEditing] = useState<MonitoredEndpoint | null>(null)
  const [historyOpenId, setHistoryOpenId] = useState<number | null>(null)

  useEffect(() => {
    void dispatch(fetchHealth())
    void dispatch(fetchEndpoints())
  }, [dispatch])

  async function handleCreate(payload: EndpointInput) {
    await dispatch(createEndpoint(payload)).unwrap()
  }

  async function handleUpdate(payload: EndpointInput) {
    if (!editing) return
    await dispatch(updateEndpoint({ id: editing.id, payload })).unwrap()
    setEditing(null)
  }

  async function handleDelete(endpoint: MonitoredEndpoint) {
    const confirmed = window.confirm(`Delete “${endpoint.name}”?`)
    if (!confirmed) return
    if (editing?.id === endpoint.id) {
      setEditing(null)
    }
    if (historyOpenId === endpoint.id) {
      setHistoryOpenId(null)
    }
    await dispatch(deleteEndpoint(endpoint.id))
  }

  function toggleHistory(endpointId: number) {
    if (historyOpenId === endpointId) {
      setHistoryOpenId(null)
      return
    }
    setHistoryOpenId(endpointId)
    void dispatch(fetchEndpointHistory(endpointId))
  }

  const dueCount = endpoints.items.filter((item) => item.is_active && item.is_due).length

  return (
    <main className="app">
      <header className="app__header">
        <p className="app__brand">Apollo</p>
        <h1>API Health Monitor</h1>
        <p className="app__lede">
          Add endpoints, probe them on a schedule, and review check history.
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

      <section className="app__form-section">
        <h2>{editing ? `Edit ${editing.name}` : "Add endpoint"}</h2>
        <EndpointForm
          key={editing ? `edit-${editing.id}` : "create"}
          initial={editing}
          saving={endpoints.saving}
          onSubmit={editing ? handleUpdate : handleCreate}
          onCancel={editing ? () => setEditing(null) : undefined}
        />
      </section>

      <section className="app__endpoints">
        <div className="app__endpoints-head">
          <h2>Endpoints</h2>
          <div className="app__endpoints-actions">
            <button
              type="button"
              className="app__button"
              onClick={() => void dispatch(checkDueEndpoints())}
              disabled={endpoints.checkingDue || dueCount === 0}
            >
              {endpoints.checkingDue
                ? "Checking due…"
                : dueCount > 0
                  ? `Check due (${dueCount})`
                  : "Nothing due"}
            </button>
            <button
              type="button"
              className="app__button"
              onClick={() => void dispatch(fetchEndpoints())}
              disabled={endpoints.loading}
            >
              Refresh
            </button>
          </div>
        </div>

        {endpoints.loading && endpoints.items.length === 0 && <p>Loading…</p>}
        {endpoints.error && <p className="app__error">{endpoints.error}</p>}
        {!endpoints.loading && endpoints.items.length === 0 && (
          <p>No endpoints yet. Add one above or run `poetry run python manage.py seed`.</p>
        )}

        <ul className="app__list">
          {endpoints.items.map((endpoint) => {
            const last = endpoint.last_check
            const pillClass = last
              ? `app__pill app__pill--${last.status}`
              : "app__pill"
            const checking = endpoints.checkingId === endpoint.id
            const deleting = endpoints.deletingId === endpoint.id
            const historyOpen = historyOpenId === endpoint.id
            const history = endpoints.historyById[endpoint.id]

            return (
              <li key={endpoint.id} className="app__row-block">
                <div className="app__row">
                  <div>
                    <p className="app__row-name">
                      {endpoint.name}
                      {!endpoint.is_active && (
                        <span className="app__muted"> · inactive</span>
                      )}
                      {endpoint.is_active && endpoint.is_due && (
                        <span className="app__due"> · due</span>
                      )}
                    </p>
                    <p className="app__row-url">
                      {endpoint.method} {endpoint.url}
                    </p>
                    <p className="app__row-meta">
                      every {endpoint.check_interval_minutes} min
                    </p>
                    <p className={pillClass}>
                      {statusLabel(last?.status)}
                      {last?.latency_ms != null ? ` · ${last.latency_ms}ms` : ""}
                      {last?.status_code != null ? ` · HTTP ${last.status_code}` : ""}
                    </p>
                  </div>
                  <div className="app__row-actions">
                    <button
                      type="button"
                      className="app__button"
                      disabled={checking || !endpoint.is_active}
                      onClick={() => void dispatch(checkEndpoint(endpoint.id))}
                    >
                      {checking ? "Checking…" : "Check"}
                    </button>
                    <button
                      type="button"
                      className="app__button"
                      aria-expanded={historyOpen}
                      onClick={() => toggleHistory(endpoint.id)}
                    >
                      {historyOpen ? "Hide history" : "History"}
                    </button>
                    <button
                      type="button"
                      className="app__button"
                      onClick={() => setEditing(endpoint)}
                      disabled={deleting}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="app__button app__button--danger"
                      disabled={deleting}
                      onClick={() => void handleDelete(endpoint)}
                    >
                      {deleting ? "Deleting…" : "Delete"}
                    </button>
                  </div>
                </div>

                {historyOpen && (
                  <div className="app__history">
                    <div className="app__history-head">
                      <h3>Recent checks</h3>
                      <button
                        type="button"
                        className="app__button"
                        disabled={history?.loading}
                        onClick={() => void dispatch(fetchEndpointHistory(endpoint.id))}
                      >
                        {history?.loading ? "Refreshing…" : "Refresh history"}
                      </button>
                    </div>
                    <CheckHistory
                      items={history?.items ?? []}
                      loading={history?.loading ?? true}
                      error={history?.error ?? null}
                    />
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </section>
    </main>
  )
}

export default App
