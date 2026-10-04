const configuredBase = import.meta.env.VITE_API_URL?.trim() || '/api'
export const API_BASE = configuredBase.replace(/\/$/, '')

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
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
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
      if (response.status === 409) message = 'Keep practicing. MISTIQ needs more interaction history before it can identify reliable patterns.'
      if (response.status === 503) message = 'The learning prediction service is not ready yet. Your practice can continue when it is available.'
    } catch { /* Keep the student-facing fallback. */ }
    throw new ApiError(message, response.status, code)
  }
  return response.json() as Promise<T>
}
