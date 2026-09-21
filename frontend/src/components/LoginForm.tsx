import { useState } from "react"
import type { FormEvent } from "react"

import { useAppDispatch, useAppSelector } from "../store/hooks"
import { login } from "../store/authSlice"

export function LoginForm() {
  const dispatch = useAppDispatch()
  const { loading, error } = useAppSelector((state) => state.auth)
  const [username, setUsername] = useState("apollo")
  const [password, setPassword] = useState("apollo")

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await dispatch(login({ username, password }))
  }

  return (
    <section className="login">
      <header className="login__header">
        <p className="app__brand">Apollo</p>
        <h1>Sign in</h1>
        <p className="app__lede">
          Use the seeded demo account (`apollo` / `apollo`) or your own user.
        </p>
      </header>

      <form className="login__form" onSubmit={(event) => void handleSubmit(event)}>
        <label>
          Username
          <input
            required
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            required
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && <p className="app__error">{error}</p>}
        <button type="submit" className="app__button" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </section>
  )
}
