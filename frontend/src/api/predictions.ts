import { request } from './client'
import type { Prediction, PredictionExplanation } from '../types/entities'

export interface TelemetryData {
  student_id: number
  attempt_count: number
  predicted_error: string
  probability: number
  confidence: number
  status: string
  model_version: string
  probabilities: Record<string, number>
  logits: Record<string, number>
  raw_features: Record<string, number>
  normalized_features: Record<string, number>
  feature_attributions: Record<string, number>
  inference_latency_ms: number
  classes: string[]
}

export interface SimulationResult {
  predicted_error: string
  probability: number
  confidence: number
  status: string
  probabilities: Record<string, number>
  logits: Record<string, number>
  raw_features: Record<string, number>
  normalized_features: Record<string, number>
  feature_attributions: Record<string, number>
  inference_latency_ms: number
  model_version: string
  classes: string[]
}

export const getLatestPrediction = (id: number) => request<Prediction>(`/predictions/${id}/latest`)
export const getLatestExplanation = (id: number) => request<PredictionExplanation>(`/predictions/${id}/latest/explanation`)
export const getStudentTelemetry = (id: number) => request<TelemetryData>(`/predictions/${id}/telemetry`)
export const simulatePrediction = (payload: { preset?: string; features?: Record<string, number>; attempt_count?: number }) =>
  request<SimulationResult>('/predictions/simulate', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: { 'Content-Type': 'application/json' },
  })
