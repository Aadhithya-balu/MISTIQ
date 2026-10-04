import { request } from './client'

export type ResearchModel = Record<string, any>
export type ResearchPrediction = Record<string, any>
export const getResearchModel = () => request<ResearchModel>('/research/model')
export const getResearchPredictions = (studentId: number) => request<ResearchPrediction[]>(`/research/students/${studentId}/predictions`)
export const getPredictionTrace = (predictionId: number) => request<ResearchPrediction>(`/research/prediction/${predictionId}/trace`)
export const getResearchEvaluation = () => request<ResearchPrediction>('/research/evaluation')
export const getResearchAblations = () => request<ResearchPrediction>('/research/evaluation/ablations')
export const getResearchSeeds = () => request<ResearchPrediction>('/research/evaluation/seeds')
export const getResearchCurves = () => request<ResearchPrediction>('/research/evaluation/learning-curves')
export const getResearchColdStart = () => request<ResearchPrediction>('/research/evaluation/cold-start')
export const getResearchCalibration = (model = 'mistiq-ampa', seed = 42) => request<ResearchPrediction>(`/research/evaluation/calibration?model=${encodeURIComponent(model)}&seed=${seed}`)
export const getResearchConfusion = (model = 'mistiq-ampa', seed = 42) => request<ResearchPrediction>(`/research/evaluation/confusion-matrix?model=${encodeURIComponent(model)}&seed=${seed}`)
