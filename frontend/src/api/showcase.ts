import { request } from './client'

export interface ShowcaseStatus {
  student_id: number
  student_name: string | null
  seeded: boolean
  attempt_count: number
  mistake_count: number
  has_learner_state: boolean
  latest_prediction_error: string | null
  latest_prediction_status: string | null
  latest_attempt_question_id: number | null
}

export interface DatabaseInspection {
  counts: {
    students: number
    questions: number
    attempts: number
    mistake_events: number
    predictions: number
    recommendations: number
    learner_states: number
  }
  latest_attempt: {
    attempt_id: number
    student_id: number
    question_id: number
    correct: boolean
    timestamp: string
  } | null
  latest_mistake: {
    mistake_event_id: number
    student_id: number
    error_type: string
    topic: string
    timestamp: string
  } | null
  latest_prediction: {
    id: number
    student_id: number
    predicted_error: string
    probability: number
    status: string
    created_at: string
  } | null
}

export interface ShowcaseResetResult {
  reset: boolean
  student_id: number
  student_name: string
}

export interface SeedResult {
  attempts_seeded: number
  latest_prediction_error: string | null
  latest_prediction_status: string | null
}

export const getShowcaseStatus = () => request<ShowcaseStatus>('/showcase/status')
export const getDatabaseInspection = () => request<DatabaseInspection>('/research/database/inspection')
export const resetShowcase = () => request<ShowcaseResetResult>('/showcase/reset', { method: 'POST' })
export const seedShowcase = () => request<SeedResult>('/showcase/seed', { method: 'POST' })