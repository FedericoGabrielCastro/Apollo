import { useAppDispatch, useAppSelector } from "../store/hooks"
import { fetchDashboard, setDashboardHours } from "../store/dashboardSlice"

function formatPercent(value: number | null) {
  if (value == null) return "n/a"
  return `${value}%`
}

function formatLatency(value: number | null) {
  if (value == null) return "n/a"
  return `${value}ms`
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

export function DashboardPanel() {
  const dispatch = useAppDispatch()
  const { data, loading, error, hours } = useAppSelector((state) => state.dashboard)
  const summary = data?.summary

  return (
    <section className="dashboard">
      <div className="dashboard__head">
        <h2>Dashboard</h2>
        <div className="dashboard__controls">
          <label>
            Window
            <select
              value={hours}
              onChange={(event) => {
                const next = Number(event.target.value)
                dispatch(setDashboardHours(next))
                void dispatch(fetchDashboard(next))
              }}
            >
              <option value={1}>1h</option>
              <option value={6}>6h</option>
              <option value={24}>24h</option>
              <option value={72}>72h</option>
              <option value={168}>7d</option>
            </select>
          </label>
          <button
            type="button"
            className="app__button"
            disabled={loading}
            onClick={() => void dispatch(fetchDashboard(hours))}
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {error && <p className="app__error">{error}</p>}
      {loading && !summary && <p>Loading dashboard…</p>}

      {summary && (
        <>
          <div className="dashboard__stats">
            <div>
              <p className="dashboard__label">Uptime</p>
              <p className="dashboard__value">{formatPercent(summary.uptime_percent)}</p>
            </div>
            <div>
              <p className="dashboard__label">Checks</p>
              <p className="dashboard__value">{summary.checks_total}</p>
            </div>
            <div>
              <p className="dashboard__label">Avg latency</p>
              <p className="dashboard__value">{formatLatency(summary.avg_latency_ms)}</p>
            </div>
            <div>
              <p className="dashboard__label">Due now</p>
              <p className="dashboard__value">{summary.endpoints_due}</p>
            </div>
            <div>
              <p className="dashboard__label">Alerts</p>
              <p className="dashboard__value">{summary.alerts_total}</p>
            </div>
            <div>
              <p className="dashboard__label">Open incidents</p>
              <p className="dashboard__value">{summary.open_incidents ?? 0}</p>
            </div>
            <div>
              <p className="dashboard__label">Active endpoints</p>
              <p className="dashboard__value">
                {summary.endpoints_active}/{summary.endpoints_total}
              </p>
            </div>
          </div>

          <div className="dashboard__tables">
            <div>
              <h3>Per-endpoint uptime</h3>
              {data?.endpoints.length === 0 ? (
                <p className="check-history__empty">No endpoints yet.</p>
              ) : (
                <table className="dashboard__table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Uptime</th>
                      <th>Latency</th>
                      <th>Last</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.endpoints.map((row) => (
                      <tr key={row.id}>
                        <td>
                          {row.name}
                          {row.is_due ? <span className="app__due"> · due</span> : null}
                        </td>
                        <td>{formatPercent(row.uptime_percent)}</td>
                        <td>{formatLatency(row.avg_latency_ms)}</td>
                        <td>
                          <span
                            className={
                              row.last_status
                                ? `app__pill app__pill--${row.last_status}`
                                : "app__pill"
                            }
                          >
                            {row.last_status ?? "never"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div>
              <h3>Recent failures</h3>
              {data?.recent_failures.length === 0 ? (
                <p className="check-history__empty">No failures in this window.</p>
              ) : (
                <ul className="dashboard__list">
                  {data?.recent_failures.map((item) => (
                    <li key={item.id}>
                      <strong>{item.endpoint_name}</strong> · {item.status}
                      {item.status_code != null ? ` · HTTP ${item.status_code}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {data?.open_incident_list && data.open_incident_list.length > 0 && (
            <div className="dashboard__incidents">
              <h3>Open incidents</h3>
              <ul className="dashboard__list">
                {data.open_incident_list.map((incident) => (
                  <li key={incident.id}>
                    <strong>{incident.endpoint_name}</strong>
                    <span className="app__badge app__badge--incident">open</span>
                    <p className="dashboard__incident-summary">{incident.summary}</p>
                    <p className="status-page__meta">Opened {formatTime(incident.opened_at)}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  )
}
