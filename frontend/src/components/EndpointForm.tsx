import { useEffect, useState } from "react"
import type { FormEvent } from "react"

import type { EndpointInput, MonitoredEndpoint } from "../store/endpointsSlice"

const METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"] as const

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
  tags: [],
}

type EndpointFormProps = {
  initial?: MonitoredEndpoint | null
  saving: boolean
  onSubmit: (payload: EndpointInput) => Promise<unknown>
  onCancel?: () => void
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

  useEffect(() => {
    setForm(initial ? toInput(initial) : EMPTY_FORM)
    setTagsText(initial ? (initial.tags ?? []).join(", ") : "")
  }, [initial])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const tags = tagsText
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean)
    await onSubmit({ ...form, tags })
    if (!initial) {
      setForm(EMPTY_FORM)
      setTagsText("")
    }
  }

  const isEdit = Boolean(initial)

  return (
    <form className="endpoint-form" onSubmit={(event) => void handleSubmit(event)}>
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
          Webhook URL
          <input
            type="url"
            placeholder="https://hooks.example.com/apollo"
            value={form.webhook_url}
            onChange={(event) => setForm({ ...form, webhook_url: event.target.value })}
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
