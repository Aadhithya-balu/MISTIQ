import { request } from './client'
import type { Prediction, PredictionExplanation } from '../types/entities'

export const getLatestPrediction = (id: number) => request<Prediction>(`/predictions/${id}/latest`)
export const getLatestExplanation = (id: number) => request<PredictionExplanation>(`/predictions/${id}/latest/explanation`)
