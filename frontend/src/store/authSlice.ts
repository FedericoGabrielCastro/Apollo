import { createAsyncThunk, createSlice } from "@reduxjs/toolkit"

import { apiFetch, readError, setStoredToken, getStoredToken } from "../api/client"

export type AuthUser = {
  id: number
  username: string
  email: string
  is_staff: boolean
}

type AuthState = {
  token: string | null
  user: AuthUser | null
  bootstrapping: boolean
  loading: boolean
  error: string | null
}

const initialState: AuthState = {
  token: getStoredToken(),
  user: null,
  bootstrapping: Boolean(getStoredToken()),
  loading: false,
  error: null,
}

export const bootstrapAuth = createAsyncThunk(
  "auth/bootstrap",
  async (): Promise<AuthUser | null> => {
    const token = getStoredToken()
    if (!token) return null

    const response = await apiFetch("/api/auth/me/")
    if (!response.ok) {
      setStoredToken(null)
      throw new Error(await readError(response, "Session expired"))
    }
    return response.json()
  },
)

export const login = createAsyncThunk(
  "auth/login",
  async (payload: { username: string; password: string }) => {
    const response = await apiFetch("/api/auth/login/", {
      method: "POST",
      auth: false,
      json: payload,
    })
    if (!response.ok) {
      throw new Error(await readError(response, "Login failed"))
    }
    const data: { token: string; user: AuthUser } = await response.json()
    setStoredToken(data.token)
    return data
  },
)

export const logout = createAsyncThunk("auth/logout", async () => {
  const response = await apiFetch("/api/auth/logout/", { method: "POST" })
  setStoredToken(null)
  if (!response.ok && response.status !== 401) {
    throw new Error(await readError(response, "Logout failed"))
  }
})

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    clearAuthError(state) {
      state.error = null
    },
    forceLogout(state) {
      state.token = null
      state.user = null
      state.bootstrapping = false
      state.loading = false
      setStoredToken(null)
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(bootstrapAuth.pending, (state) => {
        state.bootstrapping = true
        state.error = null
      })
      .addCase(bootstrapAuth.fulfilled, (state, action) => {
        state.bootstrapping = false
        state.user = action.payload
        if (!action.payload) {
          state.token = null
        }
      })
      .addCase(bootstrapAuth.rejected, (state, action) => {
        state.bootstrapping = false
        state.token = null
        state.user = null
        state.error = action.error.message ?? "Session expired"
      })
      .addCase(login.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false
        state.token = action.payload.token
        state.user = action.payload.user
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? "Login failed"
      })
      .addCase(logout.fulfilled, (state) => {
        state.token = null
        state.user = null
        state.loading = false
      })
      .addCase(logout.rejected, (state) => {
        state.token = null
        state.user = null
        state.loading = false
      })
  },
})

export const { clearAuthError, forceLogout } = authSlice.actions
export default authSlice.reducer
