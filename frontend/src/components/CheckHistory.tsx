import type { HealthCheckResult } from "../store/endpointsSlice"

type CheckHistoryProps = {
  items: HealthCheckResult[]
  loading: boolean
  error: string | null
}

function formatCheckedAt(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

export function CheckHistory({ items, loading, error }: CheckHistoryProps) {
  if (loading && items.length === 0) {
    return <p className="check-history__empty">Loading history…</p>
  }

  if (error) {
    return <p className="app__error">{error}</p>
  }

  if (items.length === 0) {
    return <p className="check-history__empty">No checks recorded yet.</p>
  }

  return (
    <ol className="check-history">
      {items.map((item) => (
        <li key={item.id} className="check-history__item">
          <span className={`app__pill app__pill--${item.status}`}>{item.status}</span>
          <span className="check-history__meta">
            {item.status_code != null ? `HTTP ${item.status_code}` : "no status"}
            {item.latency_ms != null ? ` · ${item.latency_ms}ms` : ""}
          </span>
          <time dateTime={item.checked_at}>{formatCheckedAt(item.checked_at)}</time>
          {item.error_message ? (
            <p className="check-history__error">{item.error_message}</p>
          ) : null}
        </li>
      ))}
    </ol>
  )
}
