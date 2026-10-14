const configuredBase = import.meta.env.VITE_API_URL?.trim() || '/api'
export const API_BASE = configuredBase.replace(/\/$/, '')

const TOKEN_KEY = 'mistiq.token'

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

export function setToken(token: string | null): void {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY) } catch { /* storage unavailable */ }
}

export const UNAUTHORIZED_EVENT = 'mistiq:unauthorized'

export class ApiError extends Error {
  status: number
  code?: string
  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError('MISTIQ could not reach the learning service. Check that the backend is running.', 0)
  }
  if (!response.ok) {
    let message = 'The request could not be completed. Please try again.'
    let code: string | undefined
    try {
      const body = await response.json() as { detail?: string; error?: string; message?: string }
      message = body.detail || body.message || message
      code = body.error
      if (response.status === 401 && code !== 'invalid_credentials') message = 'Your session has ended. Please sign in again.'
      if (response.status === 403) message = body.detail || 'You do not have access to this area.'
      if (response.status === 409 && code === 'insufficient_data') message = 'Keep practicing. MISTIQ needs more interaction history before it can identify reliable patterns.'
      if (response.status === 503) message = 'The learning prediction service is not ready yet. Your practice can continue when it is available.'
    } catch { /* Keep the student-facing fallback. */ }
    if (response.status === 401 && code !== 'invalid_credentials') {
      setToken(null)
      try { window.dispatchEvent(new Event(UNAUTHORIZED_EVENT)) } catch { /* no window */ }
    }
    throw new ApiError(message, response.status, code)
  }
  return response.json() as Promise<T>
}
