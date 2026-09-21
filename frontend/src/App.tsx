import { useEffect, useState } from "react"
import { Link, Navigate, Route, Routes } from "react-router-dom"

import { AlertHistory } from "./components/AlertHistory"
import { CheckHistory } from "./components/CheckHistory"
import { DashboardPanel } from "./components/DashboardPanel"
import { EndpointForm } from "./components/EndpointForm"
import { LoginForm } from "./components/LoginForm"
import { StatusPageConfigForm } from "./components/StatusPageConfigForm"
import { useAppDispatch, useAppSelector } from "./store/hooks"
import {
  bootstrapAuth,
  forceLogout,
  logout,
} from "./store/authSlice"
import { fetchDashboard } from "./store/dashboardSlice"
import {
  checkDueEndpoints,
  checkEndpoint,
  createEndpoint,
  deleteEndpoint,
  fetchEndpointAlerts,
  fetchEndpointHistory,
  fetchEndpoints,
  testEndpointWebhook,
  updateEndpoint,
  type EndpointInput,
  type MonitoredEndpoint,
} from "./store/endpointsSlice"
import { fetchHealth } from "./store/healthSlice"
import { fetchIncidents } from "./store/incidentsSlice"
import "./App.css"

function statusLabel(status: string | undefined) {
  if (!status) return "never checked"
  return status
}

function AuthenticatedApp() {
  const dispatch = useAppDispatch()
  const auth = useAppSelector((state) => state.auth)
  const health = useAppSelector((state) => state.health)
  const endpoints = useAppSelector((state) => state.endpoints)
  const dashboard = useAppSelector((state) => state.dashboard)
  const [editing, setEditing] = useState<MonitoredEndpoint | null>(null)
  const [historyOpenId, setHistoryOpenId] = useState<number | null>(null)
  const [alertsOpenId, setAlertsOpenId] = useState<number | null>(null)

  useEffect(() => {
    void dispatch(fetchHealth())
    void dispatch(fetchEndpoints())
    void dispatch(fetchDashboard(dashboard.hours))
    void dispatch(fetchIncidents("open"))
  }, [dispatch, dashboard.hours])

  async function handleCreate(payload: EndpointInput) {
    await dispatch(createEndpoint(payload)).unwrap()
    void dispatch(fetchDashboard(dashboard.hours))
    void dispatch(fetchIncidents("open"))
  }

  async function handleUpdate(payload: EndpointInput) {
    if (!editing) return
    await dispatch(updateEndpoint({ id: editing.id, payload })).unwrap()
    setEditing(null)
    void dispatch(fetchDashboard(dashboard.hours))
    void dispatch(fetchIncidents("open"))
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
    if (alertsOpenId === endpoint.id) {
      setAlertsOpenId(null)
    }
    await dispatch(deleteEndpoint(endpoint.id))
    void dispatch(fetchDashboard(dashboard.hours))
    void dispatch(fetchIncidents("open"))
  }

  async function handleCheck(endpointId: number) {
    await dispatch(checkEndpoint(endpointId)).unwrap()
    await dispatch(fetchEndpoints())
    void dispatch(fetchDashboard(dashboard.hours))
    void dispatch(fetchIncidents("open"))
    if (alertsOpenId === endpointId) {
      const alertsPage = endpoints.alertsById[endpointId]?.page ?? 1
      void dispatch(fetchEndpointAlerts({ endpointId, page: alertsPage }))
    }
  }

  function toggleHistory(endpointId: number) {
    if (historyOpenId === endpointId) {
      setHistoryOpenId(null)
      return
    }
    setHistoryOpenId(endpointId)
    void dispatch(fetchEndpointHistory({ endpointId }))
  }

  function toggleAlerts(endpointId: number) {
    if (alertsOpenId === endpointId) {
      setAlertsOpenId(null)
      return
    }
    setAlertsOpenId(endpointId)
    void dispatch(fetchEndpointAlerts({ endpointId }))
  }

  function handleHistoryPageChange(endpointId: number, page: number) {
    void dispatch(fetchEndpointHistory({ endpointId, page }))
  }

  function handleAlertsPageChange(endpointId: number, page: number) {
    void dispatch(fetchEndpointAlerts({ endpointId, page }))
  }

  const dueCount = endpoints.items.filter((item) => item.is_active && item.is_due).length

  return (
    <main className="app">
      <header className="app__header">
        <div className="app__header-top">
          <p className="app__brand">Apollo</p>
          <div className="app__user">
            <Link to="/status" className="status-page__link">
              Public status
            </Link>
            <span>{auth.user?.username}</span>
            <button
              type="button"
              className="app__button"
              onClick={() => void dispatch(logout())}
            >
              Sign out
            </button>
          </div>
        </div>
        <h1>API Health Monitor</h1>
        <p className="app__lede">
          Authenticated monitoring with uptime metrics, schedules, and webhooks.
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

      <DashboardPanel />

      <StatusPageConfigForm />

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
            const testingWebhook = endpoints.testingWebhookId === endpoint.id
            const historyOpen = historyOpenId === endpoint.id
            const alertsOpen = alertsOpenId === endpoint.id
            const history = endpoints.historyById[endpoint.id]
            const alerts = endpoints.alertsById[endpoint.id]

            return (
              <li key={endpoint.id} className="app__row-block">
                <div className="app__row">
                  <div>
                    <p className="app__row-name">
                      {endpoint.name}
                      {endpoint.open_incident && (
                        <span className="app__badge app__badge--incident">incident</span>
                      )}
                      {!endpoint.is_active && (
                        <span className="app__muted"> · inactive</span>
                      )}
                      {endpoint.is_active && endpoint.is_due && (
                        <span className="app__due"> · due</span>
                      )}
                      {endpoint.is_public && (
                        <span className="app__muted"> · public</span>
                      )}
                      {endpoint.alert_on_failure && endpoint.webhook_url && (
                        <span className="app__muted"> · webhook</span>
                      )}
                      {endpoint.alert_on_failure && endpoint.alert_email && (
                        <span className="app__muted"> · email</span>
                      )}
                      {endpoint.alert_on_failure && endpoint.discord_webhook_url && (
                        <span className="app__muted"> · discord</span>
                      )}
                      {endpoint.alert_on_failure && endpoint.slack_webhook_url && (
                        <span className="app__muted"> · slack</span>
                      )}
                      {endpoint.auth_type && endpoint.auth_type !== "none" && (
                        <span className="app__muted"> · {endpoint.auth_type}</span>
                      )}
                      {endpoint.failure_threshold > 1 && (
                        <span className="app__muted">
                          {" "}
                          · threshold {endpoint.failure_threshold}
                        </span>
                      )}
                      {endpoint.check_ssl_expiry && (
                        <span className="app__muted"> · ssl</span>
                      )}
                      {endpoint.mute_alerts_until &&
                        new Date(endpoint.mute_alerts_until).getTime() > Date.now() && (
                          <span className="app__badge">muted</span>
                        )}
                      {(endpoint.expect_body_contains || endpoint.max_latency_ms != null) && (
                        <span className="app__muted"> · asserts</span>
                      )}
                    </p>
                    <p className="app__row-url">
                      {endpoint.method} {endpoint.url}
                    </p>
                    {endpoint.tags.length > 0 && (
                      <div className="app__tags">
                        {endpoint.tags.map((tag) => (
                          <span key={tag} className="app__tag">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="app__row-meta">
                      every {endpoint.check_interval_minutes} min
                      {endpoint.last_alert
                        ? ` · last alert ${endpoint.last_alert.event_type}`
                        : ""}
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
                      onClick={() => void handleCheck(endpoint.id)}
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
                      aria-expanded={alertsOpen}
                      onClick={() => toggleAlerts(endpoint.id)}
                    >
                      {alertsOpen ? "Hide alerts" : "Alerts"}
                    </button>
                    <button
                      type="button"
                      className="app__button"
                      disabled={!endpoint.webhook_url || testingWebhook}
                      onClick={() => void dispatch(testEndpointWebhook(endpoint.id))}
                    >
                      {testingWebhook ? "Testing…" : "Test webhook"}
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
                        onClick={() =>
                          void dispatch(
                            fetchEndpointHistory({
                              endpointId: endpoint.id,
                              page: history?.page ?? 1,
                            }),
                          )
                        }
                      >
                        {history?.loading ? "Refreshing…" : "Refresh history"}
                      </button>
                    </div>
                    <CheckHistory
                      items={history?.items ?? []}
                      loading={history?.loading ?? true}
                      error={history?.error ?? null}
                      page={history?.page ?? 1}
                      totalPages={history?.total_pages ?? 1}
                      onPageChange={(page) => handleHistoryPageChange(endpoint.id, page)}
                    />
                  </div>
                )}

                {alertsOpen && (
                  <div className="app__history">
                    <div className="app__history-head">
                      <h3>Alert events</h3>
                      <button
                        type="button"
                        className="app__button"
                        disabled={alerts?.loading}
                        onClick={() =>
                          void dispatch(
                            fetchEndpointAlerts({
                              endpointId: endpoint.id,
                              page: alerts?.page ?? 1,
                            }),
                          )
                        }
                      >
                        {alerts?.loading ? "Refreshing…" : "Refresh alerts"}
                      </button>
                    </div>
                    <AlertHistory
                      items={alerts?.items ?? []}
                      loading={alerts?.loading ?? true}
                      error={alerts?.error ?? null}
                      page={alerts?.page ?? 1}
                      totalPages={alerts?.total_pages ?? 1}
                      onPageChange={(page) => handleAlertsPageChange(endpoint.id, page)}
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

function LoginRoute() {
  const auth = useAppSelector((state) => state.auth)

  if (auth.bootstrapping) {
    return (
      <main className="app">
        <p>Restoring session…</p>
      </main>
    )
  }

  if (auth.token && auth.user) {
    return <Navigate to="/" replace />
  }

  return (
    <main className="app">
      <LoginForm />
    </main>
  )
}

function HomeRoute() {
  const auth = useAppSelector((state) => state.auth)

  if (auth.bootstrapping) {
    return (
      <main className="app">
        <p>Restoring session…</p>
      </main>
    )
  }

  if (!auth.token || !auth.user) {
    return <Navigate to="/login" replace />
  }

  return <AuthenticatedApp />
}

function App() {
  const dispatch = useAppDispatch()

  useEffect(() => {
    void dispatch(bootstrapAuth())
  }, [dispatch])

  useEffect(() => {
    function onUnauthorized() {
      dispatch(forceLogout())
    }
    window.addEventListener("apollo:unauthorized", onUnauthorized)
    return () => window.removeEventListener("apollo:unauthorized", onUnauthorized)
  }, [dispatch])

  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/" element={<HomeRoute />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
