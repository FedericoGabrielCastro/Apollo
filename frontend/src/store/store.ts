import { configureStore } from "@reduxjs/toolkit"

import authReducer from "./authSlice"
import dashboardReducer from "./dashboardSlice"
import endpointsReducer from "./endpointsSlice"
import healthReducer from "./healthSlice"

export const store = configureStore({
  reducer: {
    auth: authReducer,
    dashboard: dashboardReducer,
    health: healthReducer,
    endpoints: endpointsReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
