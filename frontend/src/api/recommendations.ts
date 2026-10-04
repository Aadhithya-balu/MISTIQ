import { request } from './client'
import type { RecommendedPractice, Recommendation } from '../types/entities'

export const getNextRecommendation = (id: number) => request<RecommendedPractice>(`/recommendations/${id}/next`)
export const getRecommendations = (id: number) => request<Recommendation[]>(`/recommendations/${id}`)
export const completeRecommendation = (id: number) => request<Recommendation>(`/recommendations/${id}/complete`, { method: 'POST' })
