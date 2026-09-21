import { configureStore } from "@reduxjs/toolkit"

import endpointsReducer from "./endpointsSlice"
import healthReducer from "./healthSlice"

export const store = configureStore({
  reducer: {
    health: healthReducer,
    endpoints: endpointsReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
