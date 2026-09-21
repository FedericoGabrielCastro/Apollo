import { createAsyncThunk, createSlice } from "@reduxjs/toolkit"

export type HealthStatus = {
  status: string
  service: string
  timestamp: string
}

type HealthState = {
  data: HealthStatus | null
  loading: boolean
  error: string | null
}

const initialState: HealthState = {
  data: null,
  loading: false,
  error: null,
}

export const fetchHealth = createAsyncThunk(
  "health/fetch",
  async (): Promise<HealthStatus> => {
    const response = await fetch("/api/health/")
    if (!response.ok) {
      throw new Error(`Health check failed (${response.status})`)
    }
    return response.json()
  },
)

const healthSlice = createSlice({
  name: "health",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchHealth.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchHealth.fulfilled, (state, action) => {
        state.loading = false
        state.data = action.payload
      })
      .addCase(fetchHealth.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? "Unknown error"
      })
  },
})

export default healthSlice.reducer
