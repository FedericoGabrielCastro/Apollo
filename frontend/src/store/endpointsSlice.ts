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
  created_at: string
  updated_at: string
  last_check: HealthCheckResult | null
}

type EndpointsState = {
  items: MonitoredEndpoint[]
  loading: boolean
  checkingId: number | null
  error: string | null
}

const initialState: EndpointsState = {
  items: [],
  loading: false,
  checkingId: null,
  error: null,
}

export const fetchEndpoints = createAsyncThunk(
  "endpoints/fetch",
  async (): Promise<MonitoredEndpoint[]> => {
    const response = await fetch("/api/endpoints/")
    if (!response.ok) {
      throw new Error(`Failed to load endpoints (${response.status})`)
    }
    return response.json()
  },
)

export const checkEndpoint = createAsyncThunk(
  "endpoints/check",
  async (endpointId: number): Promise<{ endpointId: number; result: HealthCheckResult }> => {
    const response = await fetch(`/api/endpoints/${endpointId}/check/`, {
      method: "POST",
    })
    if (!response.ok) {
      throw new Error(`Check failed (${response.status})`)
    }
    const result: HealthCheckResult = await response.json()
    return { endpointId, result }
  },
)

const endpointsSlice = createSlice({
  name: "endpoints",
  initialState,
  reducers: {},
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
      .addCase(checkEndpoint.pending, (state, action) => {
        state.checkingId = action.meta.arg
        state.error = null
      })
      .addCase(checkEndpoint.fulfilled, (state, action) => {
        state.checkingId = null
        const item = state.items.find((endpoint) => endpoint.id === action.payload.endpointId)
        if (item) {
          item.last_check = action.payload.result
        }
      })
      .addCase(checkEndpoint.rejected, (state, action) => {
        state.checkingId = null
        state.error = action.error.message ?? "Unknown error"
      })
  },
})

export default endpointsSlice.reducer
