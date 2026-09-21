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
  timeout_seconds: 5,
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
    timeout_seconds: endpoint.timeout_seconds,
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

  useEffect(() => {
    setForm(initial ? toInput(initial) : EMPTY_FORM)
  }, [initial])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await onSubmit(form)
    if (!initial) {
      setForm(EMPTY_FORM)
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
        <label className="endpoint-form__check">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
          />
          Active
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
