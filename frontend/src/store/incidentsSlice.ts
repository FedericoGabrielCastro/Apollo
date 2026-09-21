import { createAsyncThunk, createSlice } from "@reduxjs/toolkit"

import { apiFetch, readError } from "../api/client"

export type Incident = {
  id: number
  endpoint: number
  endpoint_name: string
  status: string
  summary: string
  opened_at: string
  resolved_at: string | null
  acknowledged_at: string | null
  acknowledged_by: number | null
  acknowledged_by_username: string | null
}

type IncidentsState = {
  items: Incident[]
  loading: boolean
  acknowledgingId: number | null
  error: string | null
}

const initialState: IncidentsState = {
  items: [],
  loading: false,
  acknowledgingId: null,
  error: null,
}

export const fetchIncidents = createAsyncThunk(
  "incidents/fetch",
  async (status?: string): Promise<Incident[]> => {
    const query = status ? `?status=${encodeURIComponent(status)}` : ""
    const response = await apiFetch(`/api/incidents/${query}`)
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to load incidents"))
    }
    return response.json()
  },
)

export const acknowledgeIncident = createAsyncThunk(
  "incidents/acknowledge",
  async (incidentId: number): Promise<Incident> => {
    const response = await apiFetch(`/api/incidents/${incidentId}/acknowledge/`, {
      method: "POST",
    })
    if (!response.ok) {
      throw new Error(await readError(response, "Failed to acknowledge incident"))
    }
    return response.json()
  },
)

const incidentsSlice = createSlice({
  name: "incidents",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchIncidents.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchIncidents.fulfilled, (state, action) => {
        state.loading = false
        state.items = action.payload
      })
      .addCase(fetchIncidents.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? "Unknown error"
      })
      .addCase(acknowledgeIncident.pending, (state, action) => {
        state.acknowledgingId = action.meta.arg
        state.error = null
      })
      .addCase(acknowledgeIncident.fulfilled, (state, action) => {
        state.acknowledgingId = null
        const index = state.items.findIndex((item) => item.id === action.payload.id)
        if (index >= 0) {
          state.items[index] = action.payload
        }
      })
      .addCase(acknowledgeIncident.rejected, (state, action) => {
        state.acknowledgingId = null
        state.error = action.error.message ?? "Unknown error"
      })
  },
})

export default incidentsSlice.reducer
