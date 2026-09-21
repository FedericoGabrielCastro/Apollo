import { useEffect } from "react"

import { useAppDispatch, useAppSelector } from "./store/hooks"
import { fetchHealth } from "./store/healthSlice"
import "./App.css"

function App() {
  const dispatch = useAppDispatch()
  const { data, loading, error } = useAppSelector((state) => state.health)

  useEffect(() => {
    void dispatch(fetchHealth())
  }, [dispatch])

  return (
    <main className="app">
      <header className="app__header">
        <p className="app__brand">Apollo</p>
        <h1>API Health Monitor</h1>
        <p className="app__lede">
          Scaffold ready — Django API plus React with Redux.
        </p>
      </header>

      <section className="app__status" aria-live="polite">
        <h2>Backend health</h2>
        {loading && <p>Checking…</p>}
        {error && <p className="app__error">{error}</p>}
        {data && (
          <dl>
            <div>
              <dt>Status</dt>
              <dd>{data.status}</dd>
            </div>
            <div>
              <dt>Service</dt>
              <dd>{data.service}</dd>
            </div>
            <div>
              <dt>Timestamp</dt>
              <dd>{data.timestamp}</dd>
            </div>
          </dl>
        )}
      </section>
    </main>
  )
}

export default App
