import { request } from './client'
import type { AttemptSubmission, OptionKey } from '../types/entities'

export const submitAttempt = (payload: {
  student_id: number; question_id: number; selected_option: OptionKey; response_time: number; idempotency_key: string
}) => request<AttemptSubmission>('/attempts', { method: 'POST', body: JSON.stringify(payload) })
