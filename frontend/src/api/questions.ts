import { request } from './client'
import type { Question } from '../types/entities'

export const getQuestions = (filters?: { topic?: string; subtopic?: string; difficulty?: number }) => {
  const query = new URLSearchParams()
  if (filters?.topic) query.set('topic', filters.topic)
  if (filters?.subtopic) query.set('subtopic', filters.subtopic)
  if (filters?.difficulty) query.set('difficulty', String(filters.difficulty))
  const suffix = query.size ? `?${query.toString()}` : ''
  return request<Question[]>(`/questions${suffix}`)
}
