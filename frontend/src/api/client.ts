const TOKEN_KEY = "apollo_token"

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setStoredToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

export async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body === "string") return body
    if (body.detail) return String(body.detail)
    const first = Object.values(body).flat()[0]
    if (first) return String(first)
  } catch {
    // ignore parse errors
  }
  return `${fallback} (${response.status})`
}

type ApiFetchOptions = RequestInit & {
  auth?: boolean
  json?: unknown
}

export async function apiFetch(path: string, options: ApiFetchOptions = {}): Promise<Response> {
  const { auth = true, json, headers: initHeaders, ...rest } = options
  const headers = new Headers(initHeaders)

  if (json !== undefined) {
    headers.set("Content-Type", "application/json")
  }

  if (auth) {
    const token = getStoredToken()
    if (token) {
      headers.set("Authorization", `Token ${token}`)
    }
  }

  const response = await fetch(path, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })

  if (response.status === 401 && auth) {
    setStoredToken(null)
    window.dispatchEvent(new Event("apollo:unauthorized"))
  }

  return response
}
