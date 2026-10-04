import type { ErrorType } from '../types/entities'

export const mistakeLabels: Record<ErrorType, string> = {
  CORRECT: 'Correct response', CONCEPT_CONFUSION: 'Concept confusion', CALCULATION_ERROR: 'Calculation error',
  PROCEDURE_ERROR: 'Procedure error', CARELESS_ERROR: 'Careless error', TIME_PRESSURE: 'Time pressure',
  DIFFICULTY_FAILURE: 'Difficulty challenge', REPEATED_MISTAKE: 'Repeated mistake',
}
