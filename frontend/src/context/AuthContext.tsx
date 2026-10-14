import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as authApi from '../api/auth'
import { getToken, setToken, UNAUTHORIZED_EVENT } from '../api/client'
import type { AuthUser } from '../types/entities'

interface AuthContextValue {
  user: AuthUser | null
  ready: boolean
  restoreError: string
  login: (username: string, password: string) => Promise<void>
  register: (name: string, username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [ready, setReady] = useState(false)
  const [restoreError, setRestoreError] = useState('')

  useEffect(() => {
    let active = true
    if (!getToken()) { setReady(true); return }
    authApi.getMe()
      .then(account => { if (active) setUser(account) })
      .catch(error => {
        if (!active) return
        setToken(null)
        setRestoreError(error instanceof Error ? error.message : '')
      })
      .finally(() => { if (active) setReady(true) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    ready,
    restoreError,
    login: async (username, password) => {
      const result = await authApi.login(username, password)
      setToken(result.token)
      setUser(result.user)
    },
    register: async (name, username, password) => {
      const result = await authApi.register(name, username, password)
      setToken(result.token)
      setUser(result.user)
    },
    logout: async () => {
      try { await authApi.logout() } catch { /* best effort */ }
      setToken(null)
      setUser(null)
    },
  }), [user, ready, restoreError])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
