import { useEffect, useState } from "react"
import type { FormEvent } from "react"

import type { EndpointInput, MonitoredEndpoint } from "../store/endpointsSlice"

const METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"] as const

const AUTH_TYPES = ["none", "bearer", "basic"] as const

const EMPTY_FORM: EndpointInput = {
  name: "",
  url: "",
  method: "GET",
  expected_status: 200,
  is_active: true,
  is_public: false,
  timeout_seconds: 5,
  check_interval_minutes: 5,
  webhook_url: "",
  alert_email: "",
  alert_on_failure: true,
  expect_body_contains: "",
  expect_header_name: "",
  expect_header_value: "",
  expect_json_path: "",
  expect_json_value: "",
  request_body: "",
  max_latency_ms: null,
  check_ssl_expiry: false,
  ssl_warn_days: 14,
  mute_alerts_until: null,
  quiet_hours_start: null,
  quiet_hours_end: null,
  request_headers: {},
  auth_type: "none",
  auth_username: "",
  auth_secret: "",
  failure_threshold: 1,
  discord_webhook_url: "",
  slack_webhook_url: "",
  tags: [],
}

function headersToText(headers: Record<string, string>): string {
  return Object.entries(headers)
    .map(([key, value]) => `${key}: ${value}`)
    .join("\n")
}

function textToHeaders(text: string): Record<string, string> {
  const headers: Record<string, string> = {}
  for (const line of text.split("\n")) {
    const trimmed = line.trim()
    if (!trimmed) continue
    const colon = trimmed.indexOf(":")
    if (colon <= 0) continue
    const key = trimmed.slice(0, colon).trim()
    const value = trimmed.slice(colon + 1).trim()
    if (key) headers[key] = value
  }
  return headers
}

type EndpointFormProps = {
  initial?: MonitoredEndpoint | null
  saving: boolean
  onSubmit: (payload: EndpointInput) => Promise<unknown>
  onCancel?: () => void
}

function toLocalDatetimeValue(iso: string | null): string {
  if (!iso) return ""
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ""
  const pad = (n: number) => String(n).padStart(2, "0")
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

function fromLocalDatetimeValue(value: string): string | null {
  if (!value.trim()) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString()
}

function quietHoursToInput(value: string | null): string {
  if (!value) return ""
  const match = value.match(/^(\d{2}:\d{2})/)
  return match ? match[1] : ""
}

function quietHoursFromInput(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  if (/^\d{2}:\d{2}$/.test(trimmed)) return `${trimmed}:00`
  if (/^\d{2}:\d{2}:\d{2}$/.test(trimmed)) return trimmed
  return null
}

function toInput(endpoint: MonitoredEndpoint): EndpointInput {
  return {
    name: endpoint.name,
    url: endpoint.url,
    method: endpoint.method,
    expected_status: endpoint.expected_status,
    is_active: endpoint.is_active,
    is_public: endpoint.is_public,
    timeout_seconds: endpoint.timeout_seconds,
    check_interval_minutes: endpoint.check_interval_minutes,
    webhook_url: endpoint.webhook_url,
    alert_email: endpoint.alert_email,
    alert_on_failure: endpoint.alert_on_failure,
    expect_body_contains: endpoint.expect_body_contains ?? "",
    expect_header_name: endpoint.expect_header_name ?? "",
    expect_header_value: endpoint.expect_header_value ?? "",
    expect_json_path: endpoint.expect_json_path ?? "",
    expect_json_value: endpoint.expect_json_value ?? "",
    request_body: endpoint.request_body ?? "",
    max_latency_ms: endpoint.max_latency_ms,
    check_ssl_expiry: endpoint.check_ssl_expiry,
    ssl_warn_days: endpoint.ssl_warn_days,
    mute_alerts_until: endpoint.mute_alerts_until,
    quiet_hours_start: endpoint.quiet_hours_start,
    quiet_hours_end: endpoint.quiet_hours_end,
    request_headers: endpoint.request_headers ?? {},
    auth_type: endpoint.auth_type ?? "none",
    auth_username: endpoint.auth_username ?? "",
    auth_secret: endpoint.auth_secret ?? "",
    failure_threshold: endpoint.failure_threshold ?? 1,
    discord_webhook_url: endpoint.discord_webhook_url ?? "",
    slack_webhook_url: endpoint.slack_webhook_url ?? "",
    tags: endpoint.tags ?? [],
  }
}

export function EndpointForm({
  initial = null,
  saving,
  onSubmit,
  onCancel,
}: EndpointFormProps) {
  const [form, setForm] = useState<EndpointInput>(
    initial ? toInput(initial) : EMPTY_FORM,
  )
  const [tagsText, setTagsText] = useState(
    initial ? (initial.tags ?? []).join(", ") : "",
  )
  const [muteLocal, setMuteLocal] = useState(
    initial ? toLocalDatetimeValue(initial.mute_alerts_until) : "",
  )
  const [quietStartLocal, setQuietStartLocal] = useState(
    initial ? quietHoursToInput(initial.quiet_hours_start) : "",
  )
  const [quietEndLocal, setQuietEndLocal] = useState(
    initial ? quietHoursToInput(initial.quiet_hours_end) : "",
  )
  const [maxLatencyText, setMaxLatencyText] = useState(
    initial?.max_latency_ms != null ? String(initial.max_latency_ms) : "",
  )
  const [headersText, setHeadersText] = useState(
    initial ? headersToText(initial.request_headers ?? {}) : "",
  )

  useEffect(() => {
    setForm(initial ? toInput(initial) : EMPTY_FORM)
    setTagsText(initial ? (initial.tags ?? []).join(", ") : "")
    setMuteLocal(initial ? toLocalDatetimeValue(initial.mute_alerts_until) : "")
    setQuietStartLocal(initial ? quietHoursToInput(initial.quiet_hours_start) : "")
    setQuietEndLocal(initial ? quietHoursToInput(initial.quiet_hours_end) : "")
    setMaxLatencyText(
      initial?.max_latency_ms != null ? String(initial.max_latency_ms) : "",
    )
    setHeadersText(initial ? headersToText(initial.request_headers ?? {}) : "")
  }, [initial])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const tags = tagsText
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean)
    const maxLatencyRaw = maxLatencyText.trim()
    const max_latency_ms = maxLatencyRaw === "" ? null : Number(maxLatencyRaw)
    await onSubmit({
      ...form,
      tags,
      request_headers: textToHeaders(headersText),
      max_latency_ms:
        max_latency_ms != null && Number.isFinite(max_latency_ms)
          ? max_latency_ms
          : null,
      mute_alerts_until: fromLocalDatetimeValue(muteLocal),
      quiet_hours_start: quietHoursFromInput(quietStartLocal),
      quiet_hours_end: quietHoursFromInput(quietEndLocal),
    })
    if (!initial) {
      setForm(EMPTY_FORM)
      setTagsText("")
      setMuteLocal("")
      setQuietStartLocal("")
      setQuietEndLocal("")
      setMaxLatencyText("")
      setHeadersText("")
    }
  }

  const isEdit = Boolean(initial)

  return (
    <form className="endpoint-form" onSubmit={(event) => void handleSubmit(event)}>
      <details className="endpoint-form__section" open>
        <summary>Basics</summary>
        <div className="endpoint-form__grid">
          <label>
            Name
            <input
              required
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
            />
          </label>
          <label className="endpoint-form__wide">
            URL
            <input
              required
              type="url"
              placeholder="https://example.com/health"
              value={form.url}
              onChange={(event) => setForm({ ...form, url: event.target.value })}
            />
          </label>
          <label>
            Method
            <select
              value={form.method}
              onChange={(event) => setForm({ ...form, method: event.target.value })}
            >
              {METHODS.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </label>
          <label>
            Expected status
            <input
              required
              type="number"
              min={100}
              max={599}
              value={form.expected_status}
              onChange={(event) =>
                setForm({ ...form, expected_status: Number(event.target.value) })
              }
            />
          </label>
          <label>
            Timeout (s)
            <input
              required
              type="number"
              min={1}
              max={120}
              value={form.timeout_seconds}
              onChange={(event) =>
                setForm({ ...form, timeout_seconds: Number(event.target.value) })
              }
            />
          </label>
          <label>
            Interval (min)
            <input
              required
              type="number"
              min={1}
              max={1440}
              value={form.check_interval_minutes}
              onChange={(event) =>
                setForm({
                  ...form,
                  check_interval_minutes: Number(event.target.value),
                })
              }
            />
          </label>
          <label className="endpoint-form__wide">
            Tags
            <input
              placeholder="production, api, critical"
              value={tagsText}
              onChange={(event) => setTagsText(event.target.value)}
            />
          </label>
          <label className="endpoint-form__check">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
            />
            Active
          </label>
          <label className="endpoint-form__check">
            <input
              type="checkbox"
              checked={form.is_public}
              onChange={(event) => setForm({ ...form, is_public: event.target.checked })}
            />
            Public on status page
          </label>
        </div>
      </details>

      <details className="endpoint-form__section">
        <summary>Request</summary>
        <div className="endpoint-form__grid">
          <label className="endpoint-form__wide">
            Request headers
            <textarea
              rows={3}
              placeholder={"Authorization: Bearer token\nX-Custom: value"}
              value={headersText}
              onChange={(event) => setHeadersText(event.target.value)}
            />
          </label>
          <label>
            Auth type
            <select
              value={form.auth_type}
              onChange={(event) =>
                setForm({
                  ...form,
                  auth_type: event.target.value as EndpointInput["auth_type"],
                })
              }
            >
              {AUTH_TYPES.map((authType) => (
                <option key={authType} value={authType}>
                  {authType}
                </option>
              ))}
            </select>
          </label>
          {form.auth_type === "basic" && (
            <label>
              Auth username
              <input
                value={form.auth_username}
                onChange={(event) =>
                  setForm({ ...form, auth_username: event.target.value })
                }
              />
            </label>
          )}
          {form.auth_type !== "none" && (
            <label className={form.auth_type === "bearer" ? "endpoint-form__wide" : undefined}>
              Auth secret
              <input
                type="password"
                autoComplete="off"
                placeholder={isEdit ? "Leave blank to keep current" : ""}
                value={form.auth_secret}
                onChange={(event) => setForm({ ...form, auth_secret: event.target.value })}
              />
            </label>
          )}
          <label className="endpoint-form__wide">
            Request body
            <textarea
              rows={3}
              placeholder='{"status":"ok"}'
              value={form.request_body}
              onChange={(event) => setForm({ ...form, request_body: event.target.value })}
            />
          </label>
        </div>
      </details>

      <details className="endpoint-form__section">
        <summary>Assertions</summary>
        <div className="endpoint-form__grid">
          <label className="endpoint-form__wide">
            Body must contain
            <input
              placeholder='e.g. "status":"ok"'
              value={form.expect_body_contains}
              onChange={(event) =>
                setForm({ ...form, expect_body_contains: event.target.value })
              }
            />
          </label>
          <label>
            Expected header name
            <input
              placeholder="X-Health"
              value={form.expect_header_name}
              onChange={(event) =>
                setForm({ ...form, expect_header_name: event.target.value })
              }
            />
          </label>
          <label>
            Expected header value
            <input
              placeholder="green"
              value={form.expect_header_value}
              onChange={(event) =>
                setForm({ ...form, expect_header_value: event.target.value })
              }
            />
          </label>
          <label>
            JSON path
            <input
              placeholder="$.status"
              value={form.expect_json_path}
              onChange={(event) =>
                setForm({ ...form, expect_json_path: event.target.value })
              }
            />
          </label>
          <label>
            JSON expected value
            <input
              placeholder="ok"
              value={form.expect_json_value}
              onChange={(event) =>
                setForm({ ...form, expect_json_value: event.target.value })
              }
            />
          </label>
          <label>
            Max latency (ms)
            <input
              type="number"
              min={1}
              placeholder="optional"
              value={maxLatencyText}
              onChange={(event) => setMaxLatencyText(event.target.value)}
            />
          </label>
          <label>
            SSL warn days
            <input
              required
              type="number"
              min={1}
              max={365}
              value={form.ssl_warn_days}
              onChange={(event) =>
                setForm({ ...form, ssl_warn_days: Number(event.target.value) })
              }
            />
          </label>
          <label className="endpoint-form__check">
            <input
              type="checkbox"
              checked={form.check_ssl_expiry}
              onChange={(event) =>
                setForm({ ...form, check_ssl_expiry: event.target.checked })
              }
            />
            Check SSL certificate expiry
          </label>
        </div>
      </details>

      <details className="endpoint-form__section">
        <summary>Alerts</summary>
        <div className="endpoint-form__grid">
          <label className="endpoint-form__wide">
            Webhook URL
            <input
              type="url"
              placeholder="https://hooks.example.com/apollo"
              value={form.webhook_url}
              onChange={(event) => setForm({ ...form, webhook_url: event.target.value })}
            />
          </label>
          <label className="endpoint-form__wide">
            Discord webhook URL
            <input
              type="url"
              placeholder="https://example.com/hooks/discord"
              value={form.discord_webhook_url}
              onChange={(event) =>
                setForm({ ...form, discord_webhook_url: event.target.value })
              }
            />
          </label>
          <label className="endpoint-form__wide">
            Slack webhook URL
            <input
              type="url"
              placeholder="https://example.com/hooks/slack"
              value={form.slack_webhook_url}
              onChange={(event) =>
                setForm({ ...form, slack_webhook_url: event.target.value })
              }
            />
          </label>
          <label className="endpoint-form__wide">
            Alert email
            <input
              type="email"
              placeholder="ops@example.com"
              value={form.alert_email}
              onChange={(event) => setForm({ ...form, alert_email: event.target.value })}
            />
          </label>
          <label>
            Failure threshold
            <input
              required
              type="number"
              min={1}
              max={20}
              value={form.failure_threshold}
              onChange={(event) =>
                setForm({ ...form, failure_threshold: Number(event.target.value) })
              }
            />
          </label>
          <label className="endpoint-form__wide">
            Mute alerts until
            <input
              type="datetime-local"
              value={muteLocal}
              onChange={(event) => setMuteLocal(event.target.value)}
            />
          </label>
          <div className="endpoint-form__wide endpoint-form__quiet-hours">
            <span className="endpoint-form__quiet-label">Quiet hours</span>
            <div className="endpoint-form__quiet-row">
              <label>
                Start
                <input
                  type="time"
                  value={quietStartLocal}
                  onChange={(event) => setQuietStartLocal(event.target.value)}
                />
              </label>
              <label>
                End
                <input
                  type="time"
                  value={quietEndLocal}
                  onChange={(event) => setQuietEndLocal(event.target.value)}
                />
              </label>
            </div>
          </div>
          <label className="endpoint-form__check">
            <input
              type="checkbox"
              checked={form.alert_on_failure}
              onChange={(event) =>
                setForm({ ...form, alert_on_failure: event.target.checked })
              }
            />
            Alert on failure / recovery
          </label>
        </div>
      </details>

      <div className="endpoint-form__actions">
        <button type="submit" className="app__button" disabled={saving}>
          {saving ? "Saving…" : isEdit ? "Save changes" : "Add endpoint"}
        </button>
        {isEdit && onCancel && (
          <button type="button" className="app__button" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
