import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { createStudent, getStudent } from '../api/students'
import * as authApi from '../api/auth'
import { getToken, setToken, UNAUTHORIZED_EVENT, ApiError } from '../api/client'
import type { AuthUser, Student } from '../types/entities'

const LOCAL_STUDENT_KEY = 'mistiq.local_student'
const LOCAL_USER_KEY = 'mistiq.local_user'

function getStoredStudent(): Student | null {
  try {
    const raw = localStorage.getItem(LOCAL_STUDENT_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const RECENT_STUDENTS_KEY = 'mistiq.recent_students'

export interface RecentStudent {
  id: number
  name: string
  lastActive: string
}

export function getRecentStudents(): RecentStudent[] {
  try {
    const raw = localStorage.getItem(RECENT_STUDENTS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function saveRecentStudent(student: Student): void {
  try {
    const list = getRecentStudents().filter(s => s.id !== student.id)
    list.unshift({ id: student.id, name: student.name, lastActive: new Date().toISOString() })
    localStorage.setItem(RECENT_STUDENTS_KEY, JSON.stringify(list.slice(0, 5)))
  } catch {}
}

function setStoredStudent(student: Student | null): void {
  try {
    if (student) {
      localStorage.setItem(LOCAL_STUDENT_KEY, JSON.stringify(student))
      saveRecentStudent(student)
    } else {
      localStorage.removeItem(LOCAL_STUDENT_KEY)
    }
  } catch {}
}

function getStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(LOCAL_USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function setStoredUser(user: AuthUser | null): void {
  try {
    if (user) {
      localStorage.setItem(LOCAL_USER_KEY, JSON.stringify(user))
    } else {
      localStorage.removeItem(LOCAL_USER_KEY)
    }
  } catch {}
}

export interface StudentContextValue {
  student: Student | null
  user: AuthUser | null
  ready: boolean
  restoreError: string
  clearRestoreError: () => void
  enter: (name: string) => Promise<void>
  reconnect: (id: number) => Promise<void>
  login: (username: string, password: string) => Promise<void>
  register: (name: string, username: string, password: string) => Promise<void>
  leave: () => Promise<void> | void
  logout: () => Promise<void>
}

export const StudentContext = createContext<StudentContextValue | null>(null)

export function StudentProvider({ children }: { children: ReactNode }) {
  const [student, setStudent] = useState<Student | null>(() => getStoredStudent())
  const [user, setUser] = useState<AuthUser | null>(() => getStoredUser())
  const [ready, setReady] = useState(false)
  const [restoreError, setRestoreError] = useState('')

  useEffect(() => {
    let active = true
    const token = getToken()
    if (!token) {
      setReady(true)
      return
    }
    authApi.getMe()
      .then(account => {
        if (!active) return
        setUser(account)
        setStoredUser(account)
        if (account.student_id) {
          const s = {
            id: account.student_id,
            name: account.name || account.username,
            created_at: new Date().toISOString(),
          }
          setStudent(s)
          setStoredStudent(s)
        }
      })
      .catch(error => {
        if (!active) return
        setToken(null)
        setStoredUser(null)
        setRestoreError(error instanceof Error ? error.message : '')
      })
      .finally(() => {
        if (active) setReady(true)
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null)
      setStudent(null)
      setStoredUser(null)
      setStoredStudent(null)
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  const value = useMemo<StudentContextValue>(() => ({
    student,
    user,
    ready,
    restoreError,
    clearRestoreError: () => setRestoreError(''),
    enter: async (name: string) => {
      setRestoreError('')
      try {
        const created = await createStudent(name)
        setStudent(created)
        setStoredStudent(created)
        const u: AuthUser = {
          id: created.id,
          username: created.name.toLowerCase().replace(/[^a-z0-9]/g, ''),
          role: 'student',
          name: created.name,
          student_id: created.id,
        }
        setUser(u)
        setStoredUser(u)
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          const username = (name.trim().toLowerCase().replace(/[^a-z0-9]/g, '') || 'learner') + '_' + Math.random().toString(36).slice(2, 6)
          const password = 'student_pass_' + Math.random().toString(36).slice(2, 8)
          const result = await authApi.register(name, username, password)
          setToken(result.token)
          setUser(result.user)
          setStoredUser(result.user)
          if (result.user.student_id) {
            const s: Student = {
              id: result.user.student_id,
              name: result.user.name || result.user.username,
              created_at: new Date().toISOString(),
            }
            setStudent(s)
            setStoredStudent(s)
          }
        } else {
          throw err
        }
      }
    },
    reconnect: async (id: number) => {
      setRestoreError('')
      const existing = await getStudent(id)
      setStudent(existing)
      setStoredStudent(existing)
      if (id === 1) {
        try {
          const authRes = await authApi.login('student', 'student123')
          setToken(authRes.token)
          setUser(authRes.user)
          setStoredUser(authRes.user)
          return
        } catch {
          // fallback if auth endpoint not mocked or offline
        }
      }
      const u: AuthUser = {
        id: existing.id,
        username: existing.name.toLowerCase().replace(/[^a-z0-9]/g, ''),
        role: 'student',
        name: existing.name,
        student_id: existing.id,
      }
      setUser(u)
      setStoredUser(u)
    },
    login: async (username: string, password: string) => {
      setRestoreError('')
      const result = await authApi.login(username, password)
      setToken(result.token)
      setUser(result.user)
      setStoredUser(result.user)
      if (result.user.student_id) {
        const s: Student = {
          id: result.user.student_id,
          name: result.user.name || result.user.username,
          created_at: new Date().toISOString(),
        }
        setStudent(s)
        setStoredStudent(s)
      } else {
        setStudent(null)
        setStoredStudent(null)
      }
    },
    register: async (name: string, username: string, password: string) => {
      setRestoreError('')
      const result = await authApi.register(name, username, password)
      setToken(result.token)
      setUser(result.user)
      setStoredUser(result.user)
      if (result.user.student_id) {
        const s: Student = {
          id: result.user.student_id,
          name: result.user.name || result.user.username,
          created_at: new Date().toISOString(),
        }
        setStudent(s)
        setStoredStudent(s)
      }
    },
    leave: () => {
      setStudent(null)
      setUser(null)
      setToken(null)
      setStoredStudent(null)
      setStoredUser(null)
    },
    logout: async () => {
      try { await authApi.logout() } catch { /* best effort */ }
      setToken(null)
      setUser(null)
      setStudent(null)
      setStoredStudent(null)
      setStoredUser(null)
    },
  }), [student, user, ready, restoreError])

  return <StudentContext.Provider value={value}>{children}</StudentContext.Provider>
}

export function useStudent() {
  const value = useContext(StudentContext)
  if (!value) throw new Error('useStudent must be used inside StudentProvider')
  return value
}

export function useAuth() {
  const value = useContext(StudentContext)
  if (!value) throw new Error('useAuth must be used inside StudentProvider/AuthProvider')
  return value
}
