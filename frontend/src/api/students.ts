import { request } from "./client"
import type { LearnerState, MistakeEvent, MistakeSummary, Progress, Student } from "../types/entities"

export const createStudent = (name: string) => request<Student>("/students", { method: "POST", body: JSON.stringify({ name }) })
export const getStudent = (id: number) => request<Student>(`/students/${id}`)
export const getProgress = (id: number) => request<Progress>(`/students/${id}/progress`)
export const getLearnerState = (id: number) => request<LearnerState>(`/students/${id}/state`)
export const getMistakes = (id: number) => request<MistakeEvent[]>(`/students/${id}/mistakes`)
export const getMistakeSummary = (id: number) => request<MistakeSummary>(`/mistakes/${id}/summary`)
export const getRepeatedMistakes = (id: number) => request<Array<{ error_type: string; topic: string; subtopic: string | null; occurrences: number; last_occurrence: string | null; recent_occurrences: number; trend: string }>>(`/mistakes/${id}/repeated`)
export const getConceptConfusions = (id: number) => request<{ nodes: string[]; edges: Array<{ concept_a: string; concept_b: string; occurrences: number; recent_occurrences: number; last_occurrence: string | null; strength: number | null; trend: string }> }>(`/mistakes/${id}/confusions`)
export const getStudents = () => request<Student[]>(`/students`)

