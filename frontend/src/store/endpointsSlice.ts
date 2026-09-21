import { createAsyncThunk, createSlice } from "@reduxjs/toolkit"

export type HealthCheckResult = {
  id: number
  endpoint: number
  status: "up" | "down" | "error"
  status_code: number | null
  latency_ms: number | null
  error_message: string
  checked_at: string
}

export type MonitoredEndpoint = {
  id: number
  name: string
  url: string
  method: string
  expected_status: number
  is_active: boolean
  timeout_seconds: number
  check_interval_minutes: number
  created_at: string
  updated_at: string
  last_check: HealthCheckResult | null
  is_due: boolean
}

export type EndpointInput = {
  name: string
  url: string
  method: string
  expected_status: number
  is_active: boolean
  timeout_seconds: number
  check_interval_minutes: number
}

type EndpointsState = {
  items: MonitoredEndpoint[]
  loading: boolean
  saving: boolean
  checkingDue: boolean
  checkingId: number | null
  deletingId: number | null
  error: string | null
}

const initialState: EndpointsState = {
  items: [],
  loading: false,
  saving: false,
  checkingDue: false,
  checkingId: null,
  deletingId: null,
  error: null,
}

async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body === "string") return body
    if (body.detail) return String(body.detail)
    const first = Object.values(body).flat()[0]
    if (first) return String(first)
  } catch {
    // ignore parse errors
  }
  return `${fallback} (${response.status})`
}

export const fetchEndpoints = createAsyncThunk(
  "endpoints/fetch",
  async (): Promise<MonitoredEndpoint[]> => {
    const response = await fetch("/api/endpoints/")
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to load endpoints"))
    }
    return response.json()
  },
)

export const createEndpoint = createAsyncThunk(
  "endpoints/create",
  async (payload: EndpointInput): Promise<MonitoredEndpoint> => {
    const response = await fetch("/api/endpoints/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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
    const response = await fetch(`/api/endpoints/${id}/`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
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
    const response = await fetch(`/api/endpoints/${endpointId}/`, {
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
    const response = await fetch(`/api/endpoints/${endpointId}/check/`, {
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
    const response = await fetch("/api/endpoints/check-due/", {
      method: "POST",
    })
    if (!response.ok) {
      throw new Error(await readError(response, "Due check failed"))
    }
    return response.json()
  },
)

const endpointsSlice = createSlice({
  name: "endpoints",
  initialState,
  reducers: {
    clearEndpointsError(state) {
      state.error = null
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
        }
      })
      .addCase(checkDueEndpoints.rejected, (state, action) => {
        state.checkingDue = false
        state.error = action.error.message ?? "Unknown error"
      })
  },
})

export const { clearEndpointsError } = endpointsSlice.actions
export default endpointsSlice.reducer
