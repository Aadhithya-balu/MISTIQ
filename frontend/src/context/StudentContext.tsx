import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { createStudent, getStudent } from '../api/students'
import type { Student } from '../types/entities'

interface StudentContextValue {
  student: Student | null
  ready: boolean
  restoreError: string
  enter: (name: string) => Promise<void>
  reconnect: (id: number) => Promise<void>
  leave: () => void
}
const StudentContext = createContext<StudentContextValue | null>(null)

export function StudentProvider({ children }: { children: ReactNode }) {
  const [student, setStudent] = useState<Student | null>(null)
  const value = useMemo<StudentContextValue>(() => ({
    student,
    ready: true,
    restoreError: '',
    enter: async (name) => { setStudent(await createStudent(name)) },
    reconnect: async (id) => { setStudent(await getStudent(id)) },
    leave: () => { setStudent(null) },
  }), [student])
  return <StudentContext.Provider value={value}>{children}</StudentContext.Provider>
}

export function useStudent() {
  const value = useContext(StudentContext)
  if (!value) throw new Error('useStudent must be used inside StudentProvider')
  return value
}
