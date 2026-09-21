import { useState } from "react"
import type { FormEvent } from "react"

import { useAppDispatch, useAppSelector } from "../store/hooks"
import { clearAuthError, login, register } from "../store/authSlice"

type AuthMode = "login" | "register"

export function LoginForm() {
  const dispatch = useAppDispatch()
  const { loading, error } = useAppSelector((state) => state.auth)
  const [mode, setMode] = useState<AuthMode>("login")
  const [username, setUsername] = useState("apollo")
  const [password, setPassword] = useState("apollo")
  const [email, setEmail] = useState("")

  function switchMode(next: AuthMode) {
    setMode(next)
    dispatch(clearAuthError())
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (mode === "login") {
      await dispatch(login({ username, password }))
      return
    }
    await dispatch(
      register({
        username,
        password,
        ...(email.trim() ? { email: email.trim() } : {}),
      }),
    )
  }

  return (
    <section className="login">
      <header className="login__header">
        <p className="app__brand">Apollo</p>
        <h1>{mode === "login" ? "Sign in" : "Create account"}</h1>
        <p className="app__lede">
          {mode === "login"
            ? "Use the seeded demo account (`apollo` / `apollo`) or your own user."
            : "Register a new account to start monitoring endpoints."}
        </p>
      </header>

      <div className="login__tabs" role="tablist" aria-label="Authentication mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "login"}
          className={mode === "login" ? "login__tab login__tab--active" : "login__tab"}
          onClick={() => switchMode("login")}
        >
          Sign in
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "register"}
          className={mode === "register" ? "login__tab login__tab--active" : "login__tab"}
          onClick={() => switchMode("register")}
        >
          Register
        </button>
      </div>

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
        {mode === "register" && (
          <label>
            Email <span className="app__muted">(optional)</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
        )}
        <label>
          Password
          <input
            required
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && <p className="app__error">{error}</p>}
        <button type="submit" className="app__button" disabled={loading}>
          {loading
            ? mode === "login"
              ? "Signing in…"
              : "Creating account…"
            : mode === "login"
              ? "Sign in"
              : "Create account"}
        </button>
      </form>
    </section>
  )
}
