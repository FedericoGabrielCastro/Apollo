import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit"

import { apiFetch, readError } from "../api/client"

export type HealthCheckResult = {
  id: number
  endpoint: number
  status: "up" | "down" | "error"
  status_code: number | null
  latency_ms: number | null
  error_message: string
  checked_at: string
}

export type AlertEvent = {
  id: number
  endpoint: number
  check_result: number
  event_type: "failure" | "recovery"
  channel: "webhook" | "email"
  target: string
  payload: Record<string, unknown>
  success: boolean
  response_status: number | null
  error_message: string
  created_at: string
}

export type OpenIncident = {
  id: number
  endpoint: number
  endpoint_name: string
  status: string
  summary: string
  opened_at: string
  resolved_at: string | null
}

export type MonitoredEndpoint = {
  id: number
  name: string
  url: string
  method: string
  expected_status: number
  is_active: boolean
  is_public: boolean
  timeout_seconds: number
  check_interval_minutes: number
  webhook_url: string
  alert_email: string
  alert_on_failure: boolean
  tags: string[]
  created_at: string
  updated_at: string
  last_check: HealthCheckResult | null
  last_alert: AlertEvent | null
  open_incident: OpenIncident | null
  is_due: boolean
}

export type EndpointInput = {
  name: string
  url: string
  method: string
  expected_status: number
  is_active: boolean
  is_public: boolean
  timeout_seconds: number
  check_interval_minutes: number
  webhook_url: string
  alert_email: string
  alert_on_failure: boolean
  tags: string[]
}

type ListEntry<T> = {
  items: T[]
  loading: boolean
  error: string | null
}

type EndpointsState = {
  items: MonitoredEndpoint[]
  loading: boolean
  saving: boolean
  checkingDue: boolean
  checkingId: number | null
  deletingId: number | null
  testingWebhookId: number | null
  historyById: Record<number, ListEntry<HealthCheckResult>>
  alertsById: Record<number, ListEntry<AlertEvent>>
  error: string | null
}

const initialState: EndpointsState = {
  items: [],
  loading: false,
  saving: false,
  checkingDue: false,
  checkingId: null,
  deletingId: null,
  testingWebhookId: null,
  historyById: {},
  alertsById: {},
  error: null,
}

export const fetchEndpoints = createAsyncThunk(
  "endpoints/fetch",
  async (): Promise<MonitoredEndpoint[]> => {
    const response = await apiFetch("/api/endpoints/")
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to load endpoints"))
    }
    return response.json()
  },
)

export const createEndpoint = createAsyncThunk(
  "endpoints/create",
  async (payload: EndpointInput): Promise<MonitoredEndpoint> => {
    const response = await apiFetch("/api/endpoints/", {
      method: "POST",
      json: payload,
    })
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to create endpoint"))
    }
    return response.json()
  },
)

export const updateEndpoint = createAsyncThunk(
  "endpoints/update",
  async ({
    id,
    payload,
  }: {
    id: number
    payload: EndpointInput
  }): Promise<MonitoredEndpoint> => {
    const response = await apiFetch(`/api/endpoints/${id}/`, {
      method: "PUT",
      json: payload,
    })
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to update endpoint"))
    }
    return response.json()
  },
)

export const deleteEndpoint = createAsyncThunk(
  "endpoints/delete",
  async (endpointId: number): Promise<number> => {
    const response = await apiFetch(`/api/endpoints/${endpointId}/`, {
      method: "DELETE",
    })
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to delete endpoint"))
    }
    return endpointId
  },
)

export const checkEndpoint = createAsyncThunk(
  "endpoints/check",
  async (endpointId: number): Promise<{ endpointId: number; result: HealthCheckResult }> => {
    const response = await apiFetch(`/api/endpoints/${endpointId}/check/`, {
      method: "POST",
    })
    if (!response.ok) {
      throw new Error(await readError(response, "Check failed"))
    }
    const result: HealthCheckResult = await response.json()
    return { endpointId, result }
  },
)

export const checkDueEndpoints = createAsyncThunk(
  "endpoints/checkDue",
  async (): Promise<{ checked: number; results: HealthCheckResult[] }> => {
    const response = await apiFetch("/api/endpoints/check-due/", {
      method: "POST",
    })
    if (!response.ok) {
      throw new Error(await readError(response, "Due check failed"))
    }
    return response.json()
  },
)

export const fetchEndpointHistory = createAsyncThunk(
  "endpoints/fetchHistory",
  async (endpointId: number): Promise<{ endpointId: number; items: HealthCheckResult[] }> => {
    const response = await apiFetch(`/api/endpoints/${endpointId}/checks/`)
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to load history"))
    }
    const items: HealthCheckResult[] = await response.json()
    return { endpointId, items }
  },
)

export const fetchEndpointAlerts = createAsyncThunk(
  "endpoints/fetchAlerts",
  async (endpointId: number): Promise<{ endpointId: number; items: AlertEvent[] }> => {
    const response = await apiFetch(`/api/endpoints/${endpointId}/alerts/`)
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to load alerts"))
    }
    const items: AlertEvent[] = await response.json()
    return { endpointId, items }
  },
)

export const testEndpointWebhook = createAsyncThunk(
  "endpoints/testWebhook",
  async (endpointId: number): Promise<{ endpointId: number; success: boolean }> => {
    const response = await apiFetch(`/api/endpoints/${endpointId}/test-webhook/`, {
      method: "POST",
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(
        typeof body.detail === "string"
          ? body.detail
          : `Webhook test failed (${response.status})`,
      )
    }
    return { endpointId, success: Boolean(body.success) }
  },
)

function prependHistory(
  state: EndpointsState,
  endpointId: number,
  result: HealthCheckResult,
) {
  const history = state.historyById[endpointId]
  if (!history) return
  history.items = [result, ...history.items.filter((item) => item.id !== result.id)]
}

const endpointsSlice = createSlice({
  name: "endpoints",
  initialState,
  reducers: {
    clearEndpointsError(state) {
      state.error = null
    },
    clearEndpointHistory(state, action: PayloadAction<number>) {
      delete state.historyById[action.payload]
    },
    clearEndpointAlerts(state, action: PayloadAction<number>) {
      delete state.alertsById[action.payload]
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchEndpoints.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchEndpoints.fulfilled, (state, action) => {
        state.loading = false
        state.items = action.payload
      })
      .addCase(fetchEndpoints.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? "Unknown error"
      })
      .addCase(createEndpoint.pending, (state) => {
        state.saving = true
        state.error = null
      })
      .addCase(createEndpoint.fulfilled, (state, action) => {
        state.saving = false
        state.items.push(action.payload)
        state.items.sort((a, b) => a.name.localeCompare(b.name))
      })
      .addCase(createEndpoint.rejected, (state, action) => {
        state.saving = false
        state.error = action.error.message ?? "Unknown error"
      })
      .addCase(updateEndpoint.pending, (state) => {
        state.saving = true
        state.error = null
      })
      .addCase(updateEndpoint.fulfilled, (state, action) => {
        state.saving = false
        const index = state.items.findIndex((item) => item.id === action.payload.id)
        if (index >= 0) {
          state.items[index] = action.payload
        }
        state.items.sort((a, b) => a.name.localeCompare(b.name))
      })
      .addCase(updateEndpoint.rejected, (state, action) => {
        state.saving = false
        state.error = action.error.message ?? "Unknown error"
      })
      .addCase(deleteEndpoint.pending, (state, action) => {
        state.deletingId = action.meta.arg
        state.error = null
      })
      .addCase(deleteEndpoint.fulfilled, (state, action) => {
        state.deletingId = null
        state.items = state.items.filter((item) => item.id !== action.payload)
        delete state.historyById[action.payload]
        delete state.alertsById[action.payload]
      })
      .addCase(deleteEndpoint.rejected, (state, action) => {
        state.deletingId = null
        state.error = action.error.message ?? "Unknown error"
      })
      .addCase(checkEndpoint.pending, (state, action) => {
        state.checkingId = action.meta.arg
        state.error = null
      })
      .addCase(checkEndpoint.fulfilled, (state, action) => {
        state.checkingId = null
        const item = state.items.find((endpoint) => endpoint.id === action.payload.endpointId)
        if (item) {
          item.last_check = action.payload.result
          item.is_due = false
        }
        prependHistory(state, action.payload.endpointId, action.payload.result)
      })
      .addCase(checkEndpoint.rejected, (state, action) => {
        state.checkingId = null
        state.error = action.error.message ?? "Unknown error"
      })
      .addCase(checkDueEndpoints.pending, (state) => {
        state.checkingDue = true
        state.error = null
      })
      .addCase(checkDueEndpoints.fulfilled, (state, action) => {
        state.checkingDue = false
        for (const result of action.payload.results) {
          const item = state.items.find((endpoint) => endpoint.id === result.endpoint)
          if (item) {
            item.last_check = result
            item.is_due = false
          }
          prependHistory(state, result.endpoint, result)
        }
      })
      .addCase(checkDueEndpoints.rejected, (state, action) => {
        state.checkingDue = false
        state.error = action.error.message ?? "Unknown error"
      })
      .addCase(fetchEndpointHistory.pending, (state, action) => {
        const endpointId = action.meta.arg
        state.historyById[endpointId] = {
          items: state.historyById[endpointId]?.items ?? [],
          loading: true,
          error: null,
        }
      })
      .addCase(fetchEndpointHistory.fulfilled, (state, action) => {
        state.historyById[action.payload.endpointId] = {
          items: action.payload.items,
          loading: false,
          error: null,
        }
      })
      .addCase(fetchEndpointHistory.rejected, (state, action) => {
        const endpointId = action.meta.arg
        state.historyById[endpointId] = {
          items: state.historyById[endpointId]?.items ?? [],
          loading: false,
          error: action.error.message ?? "Unknown error",
        }
      })
      .addCase(fetchEndpointAlerts.pending, (state, action) => {
        const endpointId = action.meta.arg
        state.alertsById[endpointId] = {
          items: state.alertsById[endpointId]?.items ?? [],
          loading: true,
          error: null,
        }
      })
      .addCase(fetchEndpointAlerts.fulfilled, (state, action) => {
        state.alertsById[action.payload.endpointId] = {
          items: action.payload.items,
          loading: false,
          error: null,
        }
        const item = state.items.find((endpoint) => endpoint.id === action.payload.endpointId)
        if (item) {
          item.last_alert = action.payload.items[0] ?? null
        }
      })
      .addCase(fetchEndpointAlerts.rejected, (state, action) => {
        const endpointId = action.meta.arg
        state.alertsById[endpointId] = {
          items: state.alertsById[endpointId]?.items ?? [],
          loading: false,
          error: action.error.message ?? "Unknown error",
        }
      })
      .addCase(testEndpointWebhook.pending, (state, action) => {
        state.testingWebhookId = action.meta.arg
        state.error = null
      })
      .addCase(testEndpointWebhook.fulfilled, (state) => {
        state.testingWebhookId = null
      })
      .addCase(testEndpointWebhook.rejected, (state, action) => {
        state.testingWebhookId = null
        state.error = action.error.message ?? "Unknown error"
      })
  },
})

export const { clearEndpointsError, clearEndpointHistory, clearEndpointAlerts } =
  endpointsSlice.actions
export default endpointsSlice.reducer
