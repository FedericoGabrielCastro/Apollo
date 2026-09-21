import type { AlertEvent } from "../store/endpointsSlice"

type AlertHistoryProps = {
  items: AlertEvent[]
  loading: boolean
  error: string | null
}

function formatCreatedAt(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

export function AlertHistory({ items, loading, error }: AlertHistoryProps) {
  if (loading && items.length === 0) {
    return <p className="check-history__empty">Loading alerts…</p>
  }

  if (error) {
    return <p className="app__error">{error}</p>
  }

  if (items.length === 0) {
    return <p className="check-history__empty">No alerts sent yet.</p>
  }

  return (
    <ol className="check-history">
      {items.map((item) => (
        <li key={item.id} className="check-history__item">
          <span
            className={`app__pill ${
              item.event_type === "recovery" ? "app__pill--up" : "app__pill--down"
            }`}
          >
            {item.event_type}
          </span>
          <span className="check-history__meta">
            {item.channel}
            {item.success ? " · delivered" : " · failed"}
            {item.response_status != null ? ` · HTTP ${item.response_status}` : ""}
          </span>
          <time dateTime={item.created_at}>{formatCreatedAt(item.created_at)}</time>
          {item.error_message ? (
            <p className="check-history__error">{item.error_message}</p>
          ) : null}
          {item.target ? (
            <p className="check-history__target">{item.target}</p>
          ) : null}
        </li>
      ))}
    </ol>
  )
}
