import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit"

import { apiFetch, readError } from "../api/client"

export type DashboardSummary = {
  endpoints_total: number
  endpoints_active: number
  endpoints_due: number
  endpoints_with_webhook: number
  checks_total: number
  checks_up: number
  checks_down: number
  checks_error: number
  uptime_percent: number | null
  avg_latency_ms: number | null
  alerts_total: number
  alerts_failed_delivery: number
  alerts_failure_events: number
  alerts_recovery_events: number
  open_incidents: number
}

export type DashboardOpenIncident = {
  id: number
  endpoint_id: number
  endpoint_name: string
  summary: string
  opened_at: string
}

export type DashboardSeriesBucket = {
  bucket_start: string
  checks_total: number
  checks_up: number
  avg_latency_ms: number | null
  uptime_percent: number | null
}

export type DashboardEndpointRow = {
  id: number
  name: string
  url: string
  is_active: boolean
  is_due: boolean
  checks_total: number
  uptime_percent: number | null
  avg_latency_ms: number | null
  last_status: "up" | "down" | "error" | null
  last_checked_at: string | null
}

export type DashboardData = {
  window_hours: number
  generated_at: string
  summary: DashboardSummary
  series: DashboardSeriesBucket[]
  endpoints: DashboardEndpointRow[]
  recent_failures: Array<{
    id: number
    endpoint_id: number
    endpoint_name: string
    status: string
    status_code: number | null
    latency_ms: number | null
    error_message: string
    checked_at: string
  }>
  recent_alerts: Array<{
    id: number
    endpoint_id: number
    endpoint_name: string
    event_type: string
    success: boolean
    created_at: string
  }>
  open_incident_list: DashboardOpenIncident[]
}

type DashboardState = {
  data: DashboardData | null
  loading: boolean
  error: string | null
  hours: number
}

const initialState: DashboardState = {
  data: null,
  loading: false,
  error: null,
  hours: 24,
}

export const fetchDashboard = createAsyncThunk(
  "dashboard/fetch",
  async (hours: number): Promise<DashboardData> => {
    const response = await apiFetch(`/api/dashboard/?hours=${hours}`)
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to load dashboard"))
    }
    return response.json()
  },
)

const dashboardSlice = createSlice({
  name: "dashboard",
  initialState,
  reducers: {
    setDashboardHours(state, action: PayloadAction<number>) {
      state.hours = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboard.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchDashboard.fulfilled, (state, action) => {
        state.loading = false
        state.data = action.payload
        state.hours = action.payload.window_hours
      })
      .addCase(fetchDashboard.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? "Unknown error"
      })
  },
})

export const { setDashboardHours } = dashboardSlice.actions
export default dashboardSlice.reducer
