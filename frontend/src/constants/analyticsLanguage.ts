import type { AnalyticsTrend, MistakeTrend } from '../types/entities'

export const performanceTrendText: Record<AnalyticsTrend, string> = {
  IMPROVING: "You're improving in this area.",
  STABLE: 'Your performance is staying consistent.',
  DECLINING: 'This area may need some extra practice.',
  INSUFFICIENT_DATA: 'Keep practicing to reveal a clearer pattern.',
}

export const mistakeTrendText: Record<MistakeTrend, string> = {
  INCREASING: 'Showing up more often recently.',
  STABLE: 'Frequency is staying similar.',
  DECREASING: 'Showing up less often recently.',
  INSUFFICIENT_DATA: 'Keep practicing to reveal a clearer pattern.',
}
