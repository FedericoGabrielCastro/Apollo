import { useState } from "react"

import { apiFetch, readError } from "../api/client"
import { useAppDispatch, useAppSelector } from "../store/hooks"
import {
  fetchDashboard,
  setDashboardHours,
  type DashboardSeriesBucket,
} from "../store/dashboardSlice"

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

const CHART_WIDTH = 320
const CHART_HEIGHT = 72

function UptimeChart({ series }: { series: DashboardSeriesBucket[] }) {
  if (series.length === 0) {
    return <p className="check-history__empty">No check data in this window.</p>
  }

  const barWidth = CHART_WIDTH / series.length

  return (
    <svg
      viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      className="dashboard__chart"
      role="img"
      aria-label="Uptime by hour"
    >
      {series.map((bucket, index) => {
        const pct = bucket.uptime_percent ?? 0
        const barHeight = (pct / 100) * (CHART_HEIGHT - 4)
        return (
          <rect
            key={bucket.bucket_start}
            x={index * barWidth + 1}
            y={CHART_HEIGHT - barHeight}
            width={Math.max(barWidth - 2, 1)}
            height={barHeight}
            className="dashboard__chart-bar dashboard__chart-bar--uptime"
          >
            <title>
              {formatTime(bucket.bucket_start)}: {formatPercent(bucket.uptime_percent)}
            </title>
          </rect>
        )
      })}
    </svg>
  )
}

function LatencyChart({ series }: { series: DashboardSeriesBucket[] }) {
  const values = series
    .map((bucket) => bucket.avg_latency_ms)
    .filter((value): value is number => value != null)

  if (values.length === 0) {
    return <p className="check-history__empty">No latency data in this window.</p>
  }

  const max = Math.max(...values, 1)
  const barWidth = CHART_WIDTH / series.length

  return (
    <svg
      viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      className="dashboard__chart"
      role="img"
      aria-label="Average latency by hour"
    >
      {series.map((bucket, index) => {
        if (bucket.avg_latency_ms == null) return null
        const barHeight = (bucket.avg_latency_ms / max) * (CHART_HEIGHT - 4)
        return (
          <rect
            key={bucket.bucket_start}
            x={index * barWidth + 1}
            y={CHART_HEIGHT - barHeight}
            width={Math.max(barWidth - 2, 1)}
            height={barHeight}
            className="dashboard__chart-bar dashboard__chart-bar--latency"
          >
            <title>
              {formatTime(bucket.bucket_start)}: {formatLatency(bucket.avg_latency_ms)}
            </title>
          </rect>
        )
      })}
    </svg>
  )
}

async function downloadExport(path: string, filename: string) {
  const response = await apiFetch(path)
  if (!response.ok) {
    throw new Error(await readError(response, "Export failed"))
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function DashboardPanel() {
  const dispatch = useAppDispatch()
  const { data, loading, error, hours } = useAppSelector((state) => state.dashboard)
  const summary = data?.summary
  const [exportError, setExportError] = useState<string | null>(null)
  const [exporting, setExporting] = useState<string | null>(null)

  async function handleExport(path: string, filename: string, key: string) {
    setExportError(null)
    setExporting(key)
    try {
      await downloadExport(path, filename)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed")
    } finally {
      setExporting(null)
    }
  }

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

          {data?.series && data.series.length > 0 && (
            <div className="dashboard__charts">
              <div className="dashboard__chart-block">
                <h3>Uptime trend</h3>
                <UptimeChart series={data.series} />
              </div>
              <div className="dashboard__chart-block">
                <h3>Latency trend</h3>
                <LatencyChart series={data.series} />
              </div>
            </div>
          )}

          <div className="dashboard__exports">
            <h3>Exports</h3>
            <div className="dashboard__export-actions">
              <button
                type="button"
                className="app__button"
                disabled={exporting != null}
                onClick={() =>
                  void handleExport(
                    `/api/exports/checks.csv?hours=${hours}`,
                    `checks-${hours}h.csv`,
                    "checks",
                  )
                }
              >
                {exporting === "checks" ? "Downloading…" : "Checks CSV"}
              </button>
              <button
                type="button"
                className="app__button"
                disabled={exporting != null}
                onClick={() =>
                  void handleExport(
                    `/api/exports/alerts.csv?hours=${hours}`,
                    `alerts-${hours}h.csv`,
                    "alerts",
                  )
                }
              >
                {exporting === "alerts" ? "Downloading…" : "Alerts CSV"}
              </button>
              <button
                type="button"
                className="app__button"
                disabled={exporting != null}
                onClick={() =>
                  void handleExport("/api/exports/incidents.csv", "incidents.csv", "incidents")
                }
              >
                {exporting === "incidents" ? "Downloading…" : "Incidents CSV"}
              </button>
            </div>
            {exportError && <p className="app__error">{exportError}</p>}
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
