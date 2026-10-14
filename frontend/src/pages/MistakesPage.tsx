import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { getMistakes, getMistakeSummary } from '../api/students'
import { mistakeLabels } from '../constants/errorLabels'
import { mistakeTrendText, performanceTrendText } from '../constants/analyticsLanguage'
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components'
import type { ErrorType, MistakeEvent, MistakeSummary } from '../types/entities'

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.'

function TrendCopy({ value }: { value: string }) {
  if (value in performanceTrendText) return <span>{performanceTrendText[value as keyof typeof performanceTrendText]}</span>
  if (value in mistakeTrendText) return <span>{mistakeTrendText[value as keyof typeof mistakeTrendText]}</span>
  return <span>{performanceTrendText.INSUFFICIENT_DATA}</span>
}

// Educational breakdown guide for common machine learning mistakes
const MISTAKE_STUDY_GUIDE: Record<string, { trap: string; rule: string; formula?: string; tip: string }> = {
  CONCEPT_CONFUSION: {
    trap: 'Mixing up dual metrics or complementary concepts (e.g., Precision vs Recall, L1 vs L2 regularization).',
    rule: 'Precision measures prediction purity (TP / [TP + FP]), whereas Recall measures actual event coverage (TP / [TP + FN]).',
    formula: 'Precision = TP / (TP + FP)  |  Recall = TP / (TP + FN)',
    tip: 'Ask: "Does the question ask about predicted alarms or actual incidents?"',
  },
  CALCULATION_ERROR: {
    trap: 'Algebraic slip or denominator miscalculation when evaluating rates and probabilities.',
    rule: 'Always tabulate TP, FP, TN, and FN before computing quotients or percentages.',
    formula: 'Total Positives = TP + FN  |  Total Predicted Positives = TP + FP',
    tip: 'Double-check if false positives or false negatives belong in the denominator.',
  },
  TIME_PRESSURE: {
    trap: 'Rushing through question stems and missing critical qualifiers like "NOT", "EXCEPT", or "MINIMIZE".',
    rule: 'Read the prompt completely, identify the optimization goal, then evaluate option choices.',
    tip: 'Take 10 seconds to underline whether the system prioritizes low false alarms or high recall.',
  },
  DISTRACTOR_TRAP: {
    trap: 'Selecting a familiar buzzword that sounds plausible but does not mathematically solve the problem.',
    rule: 'Eliminate options that belong to adjacent topics before picking the most direct technical definition.',
    tip: 'Verify if the option is a data structure, an evaluation metric, or an optimization objective.',
  },
}

export function MistakesPage() {
  const { student, user } = useStudent()
  const studentId = student?.id ?? user?.student_id ?? (typeof (user as any)?.id === 'number' ? (user as any).id : 0)

  const [mistakes, setMistakes] = useState<MistakeEvent[]>([])
  const [analytics, setAnalytics] = useState<MistakeSummary | null>(null)
  const [repeated, setRepeated] = useState<Array<{
    error_type: string
    topic: string
    subtopic: string | null
    occurrences: number
    last_occurrence: string | null
    recent_occurrences: number
    trend: string
  }>>([])
  const [confusions, setConfusions] = useState<{
    nodes: string[]
    edges: Array<{
      concept_a: string
      concept_b: string
      occurrences: number
      recent_occurrences: number
      last_occurrence: string | null
      strength: number | null
      trend: string
    }>
  }>({ nodes: [], edges: [] })

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Interactive Mistake Mastery state stored in localStorage
  const [masteredConcepts, setMasteredConcepts] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(`mistiq.mastered_concepts_${studentId}`)
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  })

  const toggleMastered = (conceptKey: string) => {
    setMasteredConcepts(prev => {
      const next = prev.includes(conceptKey)
        ? prev.filter(k => k !== conceptKey)
        : [...prev, conceptKey]
      try {
        localStorage.setItem(`mistiq.mastered_concepts_${studentId}`, JSON.stringify(next))
      } catch {}
      return next
    })
  }

  useEffect(() => {
    if (!studentId) return
    let active = true

    getMistakeSummary(studentId)
      .then(summary => {
        if (!active) return
        setAnalytics(summary)
        setMistakes(summary.recent_mistakes)
        setRepeated(summary.repeated)
        setConfusions(summary.confusions)
      })
      .catch(() =>
        getMistakes(studentId)
          .then(list => { if (active) setMistakes(list) })
          .catch(reason => { if (active) setError(errorMessage(reason)) })
      )
      .catch(reason => {
        if (active) setError(errorMessage(reason))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [studentId])

  const groups = useMemo(
    () =>
      mistakes.reduce<Record<string, MistakeEvent[]>>((all, mistake) => {
        ;(all[mistake.error_type] ||= []).push(mistake)
        return all
      }, {}),
    [mistakes]
  )

  const distribution =
    analytics?.distribution ??
    Object.entries(groups).map(([error_type, rows]) => ({
      error_type: error_type as ErrorType,
      occurrences: rows.length,
      percentage_of_mistakes: mistakes.length ? rows.length / mistakes.length : 0,
      recent_frequency: null,
      recent_occurrences: rows.length,
      trend: 'INSUFFICIENT_DATA' as const,
      trend_value: null,
    }))

  const maxTimeline = analytics?.timeline?.length
    ? Math.max(...analytics.timeline.map(item => item.occurrences))
    : 1

  const totalMistakeCount = analytics?.mistake_count ?? mistakes.length
  const totalMasteredCount = masteredConcepts.length
  const remediationPercentage = totalMistakeCount > 0
    ? Math.min(100, Math.round((totalMasteredCount / Math.max(totalMistakeCount, 1)) * 100))
    : 0

  if (loading) {
    return (
      <>
        <PageHeader title="Mistakes" description="Patterns from your recorded practice can help you choose what to review." />
        <LoadingState label="Loading your review history…" />
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageHeader title="Mistakes" description="Patterns from your recorded practice can help you choose what to review." />
        <ErrorState message={error} />
      </>
    )
  }

  if (!mistakes.length) {
    return (
      <>
        <PageHeader title="Mistakes" description="Patterns from your recorded practice can help you choose what to review." />
        <Card>
          <EmptyState
            title="A great start"
            description="No recurring mistake patterns yet. When they do, your real review history will appear here."
          >
            <Link className="text-link" to="/practice">
              Try a practice question <span aria-hidden="true">→</span>
            </Link>
          </EmptyState>
        </Card>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Mistakes"
        description="Patterns from your recorded practice can help you choose what to review."
      />

      {/* Educational Mistake Remediation Hub Header */}
      <div className="remediation-hub-card">
        <div className="remediation-hub-copy">
          <span className="eyebrow">Mistake Learning Lab</span>
          <h2>Deconstruct Misconceptions &amp; Remediate</h2>
          <p>
            Real educational progress happens by understanding exactly why an error was made. Review the cognitive traps below, study the mental models, and launch targeted remediation drills.
          </p>
          <div className="remediation-hub-actions">
            <Link to="/practice" className="button">
              <span>🚀 Launch Targeted Practice Drill</span> <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>

        <div className="remediation-hub-metrics">
          <div className="remediation-stat-pill">
            <span className="pill-label">Logged Mistakes</span>
            <strong className="pill-value">{totalMistakeCount}</strong>
          </div>
          <div className="remediation-stat-pill">
            <span className="pill-label">Mastered Concepts</span>
            <strong className="pill-value" style={{ color: 'var(--success)' }}>{totalMasteredCount}</strong>
          </div>
          <div className="remediation-stat-pill">
            <span className="pill-label">Remediation Progress</span>
            <strong className="pill-value" style={{ color: 'var(--accent-ink)' }}>{remediationPercentage}%</strong>
          </div>
        </div>
      </div>

      <div className="mistake-analytics">
        {/* Distribution of Mistakes Card */}
        <Card className="analytics-card">
          <div className="card-kicker">Common mistakes</div>
          <h3>{analytics?.mistake_count ?? mistakes.length} recorded review moments</h3>
          <div className="performance-list">
            {distribution.map(row => {
              const guide = MISTAKE_STUDY_GUIDE[row.error_type]
              const isMastered = masteredConcepts.includes(row.error_type)
              return (
                <div className="performance-row" key={row.error_type}>
                  <div className="performance-heading">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <strong>{mistakeLabels[row.error_type]}</strong>
                      {isMastered && (
                        <span className="badge badge-success" style={{ fontSize: '10px', padding: '2px 6px' }}>
                          ✓ Mastered
                        </span>
                      )}
                    </div>
                    <span>{row.occurrences} · {Math.round(row.percentage_of_mistakes * 100)}%</span>
                  </div>
                  <div
                    className="analytics-bar mistake-bar"
                    role="img"
                    aria-label={`${mistakeLabels[row.error_type]}: ${row.occurrences} occurrences`}
                  >
                    <span style={{ width: `${Math.round(row.percentage_of_mistakes * 100)}%` }} />
                  </div>
                  <small><TrendCopy value={row.trend} /></small>

                  {/* Deep Learning Guide Box */}
                  {guide && (
                    <div className="mistake-deep-guide">
                      <div className="guide-point">
                        <span className="guide-label">Cognitive Trap:</span>
                        <span className="guide-text">{guide.trap}</span>
                      </div>
                      <div className="guide-point">
                        <span className="guide-label">Rule of Thumb:</span>
                        <span className="guide-text">{guide.rule}</span>
                      </div>
                      {guide.formula && (
                        <div className="guide-formula">
                          <code>{guide.formula}</code>
                        </div>
                      )}
                      <div className="guide-actions">
                        <Link
                          to={`/practice?error_type=${encodeURIComponent(row.error_type)}`}
                          className="button button-secondary"
                          style={{ fontSize: '11.5px', padding: '5px 10px' }}
                        >
                          Practice {mistakeLabels[row.error_type]} Questions
                        </Link>
                        <button
                          type="button"
                          className={`button ${isMastered ? 'button-secondary' : ''}`}
                          style={{ fontSize: '11.5px', padding: '5px 10px' }}
                          onClick={() => toggleMastered(row.error_type)}
                        >
                          {isMastered ? '✓ Mastered' : 'Mark Concept as Mastered'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          <p className="quiet-note">
            Only mistake patterns present in your recorded practice are shown. Very rare categories can be absent in a short session.
          </p>
        </Card>

        {/* Repeated Mistakes Card */}
        <Card className="analytics-card">
          <div className="card-kicker">Repeated mistakes</div>
          <h3>Patterns that have appeared more than once</h3>
          {repeated.length ? (
            <ul className="insight-list">
              {repeated.map((row, index) => {
                const key = `${row.error_type}-${row.topic}-${row.subtopic ?? ''}`
                const isMastered = masteredConcepts.includes(key)
                return (
                  <li key={`${key}-${index}`} className="repeated-mistake-item">
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <strong>{mistakeLabels[row.error_type as ErrorType] ?? row.error_type}</strong>
                        {isMastered && <span className="badge badge-success" style={{ fontSize: '10px' }}>✓ Resolved</span>}
                      </div>
                      <span>{row.topic}{row.subtopic ? ` · ${row.subtopic}` : ''}</span>
                      <small>{row.occurrences} occurrences · <TrendCopy value={row.trend} /></small>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <Link
                        to={`/practice?topic=${encodeURIComponent(row.topic)}${row.subtopic ? `&subtopic=${encodeURIComponent(row.subtopic)}` : ''}`}
                        className="text-link"
                      >
                        Practice this
                      </Link>
                      <button
                        type="button"
                        className="button button-secondary"
                        style={{ fontSize: '11px', padding: '4px 8px' }}
                        onClick={() => toggleMastered(key)}
                      >
                        {isMastered ? '✓' : 'Clear'}
                      </button>
                    </div>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="analytics-empty">No recurring mistake patterns yet.</p>
          )}
        </Card>

        {/* Concept Confusions Card */}
        <Card className="analytics-card">
          <div className="card-kicker">Concept confusions</div>
          <h3>Concepts mixed up in recorded answers</h3>
          {confusions.edges.length ? (
            <div className="confusion-study-container">
              <ul className="confusion-list">
                {confusions.edges.map(edge => {
                  const pairKey = `${edge.concept_a}-${edge.concept_b}`
                  const isMastered = masteredConcepts.includes(pairKey)
                  return (
                    <li key={pairKey} className="confusion-edge-card">
                      <div className="confusion-pair-header">
                        <div className="confusion-duo">
                          <strong>{edge.concept_a}</strong>
                          <span className="confusion-swap-icon" aria-hidden="true">↔</span>
                          <strong>{edge.concept_b}</strong>
                        </div>
                        {isMastered && <span className="badge badge-success">Mastered</span>}
                      </div>
                      <small>{edge.occurrences} confusion events · <TrendCopy value={edge.trend} /></small>

                      {/* Side-by-Side Mental Model Comparison */}
                      <div className="confusion-compare-grid">
                        <div className="compare-col">
                          <span className="compare-name">{edge.concept_a}</span>
                          <p className="compare-rule">
                            {edge.concept_a.toLowerCase().includes('precision')
                              ? 'Precision = TP / (TP + FP). How pure are our positive predictions?'
                              : `Target concept: Focuses on ${edge.concept_a} characteristics.`}
                          </p>
                        </div>
                        <div className="compare-col">
                          <span className="compare-name">{edge.concept_b}</span>
                          <p className="compare-rule">
                            {edge.concept_b.toLowerCase().includes('recall')
                              ? 'Recall = TP / (TP + FN). How completely did we capture actual events?'
                              : `Complementary concept: Distinguishes from ${edge.concept_b}.`}
                          </p>
                        </div>
                      </div>

                      <div className="confusion-actions">
                        <Link
                          to={`/practice?topic=Classification`}
                          className="button button-secondary"
                          style={{ fontSize: '11.5px', padding: '5px 10px' }}
                        >
                          Practice {edge.concept_a} vs {edge.concept_b}
                        </Link>
                        <button
                          type="button"
                          className="button button-secondary"
                          style={{ fontSize: '11.5px', padding: '5px 10px' }}
                          onClick={() => toggleMastered(pairKey)}
                        >
                          {isMastered ? '✓ Resolved' : 'Mark as Resolved'}
                        </button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            </div>
          ) : (
            <p className="analytics-empty">No concept confusion pairs have enough recorded evidence yet.</p>
          )}
        </Card>

        {/* Timeline Activity */}
        {analytics && (
          <Card className="analytics-card">
            <div className="card-kicker">Mistake activity</div>
            <h3>
              {analytics.timeline_sufficient
                ? `Recorded events by ${analytics.timeline_bucket}`
                : 'Mistake frequency over time'}
            </h3>
            {analytics.timeline_sufficient ? (
              <div className="timeline-bars">
                {analytics.timeline.map(point => (
                  <div className="timeline-bar-row" key={point.period}>
                    <span>{point.period}</span>
                    <div
                      className="analytics-bar mistake-bar"
                      role="img"
                      aria-label={`${point.occurrences} mistakes during ${point.period}`}
                    >
                      <span style={{ width: `${Math.max(3, Math.round((point.occurrences / maxTimeline) * 100))}%` }} />
                    </div>
                    <strong>{point.occurrences}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <p className="analytics-empty">{analytics.timeline_message}</p>
            )}
          </Card>
        )}

        {/* Chronological History Log */}
        <Card className="analytics-card">
          <div className="section-heading">
            <div>
              <div className="card-kicker">Recent mistakes</div>
              <h3>Your practice history</h3>
            </div>
            <span className="count-label">{analytics?.mistake_count ?? mistakes.length} total</span>
          </div>
          <ul className="mistake-list">
            {[...mistakes].reverse().map(item => (
              <li key={item.mistake_event_id}>
                <span className="mistake-date">
                  {new Date(item.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                </span>
                <div>
                  <strong>{item.topic}</strong>
                  <span>{item.subtopic || 'General topic'} · {mistakeLabels[item.error_type]}</span>
                </div>
                <span className="mistake-type">{mistakeLabels[item.error_type]}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}
