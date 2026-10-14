import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { getProgress } from '../api/students'
import { mistakeTrendText, performanceTrendText } from '../constants/analyticsLanguage'
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components'
import type { Progress } from '../types/entities'

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.'

function TrendCopy({ value }: { value: string }) {
  if (value in performanceTrendText) return <span>{performanceTrendText[value as keyof typeof performanceTrendText]}</span>
  if (value in mistakeTrendText) return <span>{mistakeTrendText[value as keyof typeof mistakeTrendText]}</span>
  return <span>{performanceTrendText.INSUFFICIENT_DATA}</span>
}

function AccuracyChart({ points }: { points: NonNullable<Progress['trajectory']> }) {
  if (points.length < 2) {
    return <p className="analytics-empty">Keep practicing to reveal a clearer learning trend.</p>
  }

  const x = (index: number) => 24 + (index * 552) / Math.max(1, points.length - 1)
  const accuracyLine = points.map((point, index) => `${x(index)},${124 - point.accuracy * 100}`).join(' ')
  const difficultyLine = points
    .map((point, index) => `${x(index)},${124 - ((point.difficulty - 1) / 4) * 100}`)
    .join(' ')

  return (
    <>
      <svg
        className="trajectory-chart"
        viewBox="0 0 600 150"
        role="img"
        aria-label="Cumulative accuracy and attempted difficulty by chronological attempt number"
      >
        <title>Accuracy and question difficulty across attempts</title>
        <line x1="24" y1="24" x2="576" y2="24" />
        <line x1="24" y1="74" x2="576" y2="74" />
        <line x1="24" y1="124" x2="576" y2="124" />
        <polyline points={accuracyLine} />
        <polyline className="difficulty-line" points={difficultyLine} />
        <text x="24" y="145">Attempt 1</text>
        <text x="522" y="145">Attempt {points.length}</text>
      </svg>
      <div className="chart-legend">
        <span><i className="legend-accuracy" />Cumulative accuracy</span>
        <span><i className="legend-difficulty" />Difficulty attempted (1–5)</span>
      </div>
      <p className="chart-caption">
        The difficulty line shows challenge level, not improvement. Accuracy is calculated from results through each attempt.
      </p>
    </>
  )
}

export function ProgressPage() {
  const { student, user } = useStudent()
  const studentId = student?.id ?? user?.student_id ?? (typeof (user as any)?.id === 'number' ? (user as any).id : 0)

  const [progress, setProgress] = useState<Progress | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!studentId) return
    let active = true

    getProgress(studentId)
      .then(value => { if (active) setProgress(value) })
      .catch(reason => { if (active) setError(errorMessage(reason)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [studentId])

  if (loading) {
    return (
      <>
        <PageHeader title="Your progress" description="A record of the work you have put in." />
        <LoadingState label="Loading your progress…" />
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageHeader title="Your progress" description="A record of the work you have put in." />
        <ErrorState message={error} />
      </>
    )
  }

  if (!progress?.attempt_count) {
    return (
      <>
        <PageHeader title="Your progress" description="A record of the work you have put in." />
        <Card>
          <EmptyState
            title="Your progress begins with practice"
            description="Once you answer a few questions, your attempts and accuracy will appear here. No sample results are shown."
          >
            <Link className="button" to="/practice">
              Start your first session <span aria-hidden="true">→</span>
            </Link>
          </EmptyState>
        </Card>
      </>
    )
  }

  const summary = progress.summary

  return (
    <>
      <PageHeader title="Your progress" description="A record of the work you have put in." />

      <div className="analytics-page">
        <div className="progress-stats">
          <Card>
            <span className="card-kicker">Questions attempted</span>
            <strong className="big-stat">{progress.attempt_count}</strong>
            <span className="stat-caption">
              {Number(summary?.topics_practiced ?? progress.topic_performance?.length ?? 0)} topics practiced
            </span>
          </Card>
          <Card>
            <span className="card-kicker">Overall accuracy</span>
            <strong className="big-stat">{Math.round(progress.accuracy * 100)}<small>%</small></strong>
            <span className="stat-caption">{progress.correct_count} correct of {progress.attempt_count}</span>
          </Card>
          <Card>
            <span className="card-kicker">Recent accuracy</span>
            <strong className="big-stat">
              {summary?.recent_accuracy == null ? '—' : `${Math.round(Number(summary.recent_accuracy) * 100)}%`}
            </strong>
            <span className="stat-caption">Last {Number(summary?.recent_sample_size ?? 0)} attempts</span>
          </Card>
          <Card>
            <span className="card-kicker">Current streak</span>
            <strong className="big-stat">{Number(summary?.current_streak ?? 0)}</strong>
            <span className="stat-caption">Best streak: {Number(summary?.best_streak ?? 0)}</span>
          </Card>
        </div>

        {summary && (
          <Card className="analytics-card">
            <div className="card-kicker">Recent trend</div>
            <h3><TrendCopy value={String(summary.improvement_direction ?? 'INSUFFICIENT_DATA')} /></h3>
            {summary.improvement_value == null ? (
              <p className="body-copy">Keep practicing to compare two equally sized performance windows.</p>
            ) : (
              <p className="body-copy">
                {Number(summary.improvement_value) >= 0 ? '+' : ''}
                {Math.round(Number(summary.improvement_value) * 100)} percentage points, comparing{' '}
                {String((summary.sample_sizes as Record<string, number>)?.recent ?? 0)} recent attempts with{' '}
                {String((summary.sample_sizes as Record<string, number>)?.previous ?? 0)} earlier attempts.
              </p>
            )}
          </Card>
        )}

        {!!progress.topic_performance?.length && (
          <Card className="analytics-card">
            <div className="card-kicker">Topic progress</div>
            <h3>Where you have practiced</h3>
            <div className="performance-list">
              {progress.topic_performance.map(row => (
                <div className="performance-row" key={row.topic}>
                  <div className="performance-heading">
                    <strong>{row.topic}</strong>
                    <span>{row.accuracy == null ? '—' : `${Math.round(row.accuracy * 100)}%`} · {row.attempts} attempts</span>
                  </div>
                  <div
                    className="analytics-bar"
                    role="img"
                    aria-label={`${row.topic}: ${row.accuracy == null ? 'not enough data' : `${Math.round(row.accuracy * 100)} percent accuracy`}`}
                  >
                    <span style={{ width: `${Math.round((row.accuracy ?? 0) * 100)}%` }} />
                  </div>
                  <small>
                    <TrendCopy value={row.trend} />
                    {row.recent_accuracy != null && ` Recent ${Math.round(row.recent_accuracy * 100)}%.`}
                  </small>
                  {progress.subtopic_performance
                    ?.filter(subtopic => subtopic.topic === row.topic)
                    .map(subtopic => (
                      <div className="subtopic-line" key={subtopic.subtopic}>
                        <span>{subtopic.subtopic}</span>
                        <span>{subtopic.accuracy == null ? '—' : `${Math.round(subtopic.accuracy * 100)}%`} · {subtopic.attempts}</span>
                      </div>
                    ))}
                </div>
              ))}
            </div>
          </Card>
        )}

        {!!progress.difficulty_performance?.some(row => row.attempts > 0) && (
          <Card className="analytics-card">
            <div className="card-kicker">Difficulty</div>
            <h3>Performance by challenge level</h3>
            <div className="performance-list">
              {progress.difficulty_performance
                .filter(row => row.attempts > 0)
                .map(row => (
                  <div className="performance-row" key={row.difficulty}>
                    <div className="performance-heading">
                      <strong>{['Very easy', 'Easy', 'Medium', 'Hard', 'Very hard'][row.difficulty - 1]}</strong>
                      <span>{row.accuracy == null ? '—' : `${Math.round(row.accuracy * 100)}%`} · {row.attempts} attempts</span>
                    </div>
                    <div
                      className="analytics-bar"
                      role="img"
                      aria-label={`Difficulty ${row.difficulty}: ${row.accuracy == null ? 'not enough data' : `${Math.round(row.accuracy * 100)} percent accuracy`}`}
                    >
                      <span style={{ width: `${Math.round((row.accuracy ?? 0) * 100)}%` }} />
                    </div>
                    <small>
                      {row.average_response_time == null ? '' : `Average response ${Math.round(row.average_response_time)} sec · `}
                      {row.mistake_rate == null ? '' : `${Math.round(row.mistake_rate * 100)}% incorrect`}
                    </small>
                  </div>
                ))}
            </div>
          </Card>
        )}

        {!!progress.trajectory?.length && (
          <Card className="analytics-card">
            <div className="card-kicker">Learning trend</div>
            <h3>Accuracy across your attempts</h3>
            <AccuracyChart points={progress.trajectory} />
            {summary && Number(summary.high_difficulty_attempts) > 0 && (
              <p className="chart-caption">
                Correct on {Number(summary.successful_high_difficulty_attempts)} of {Number(summary.high_difficulty_attempts)} high-difficulty attempts (levels 4–5).
              </p>
            )}
          </Card>
        )}

        {progress.recovery && (
          <Card className="analytics-card">
            <div className="card-kicker">Recovery after mistakes</div>
            <h3>
              {progress.recovery.sample_sufficient && progress.recovery.recovery_rate != null
                ? `${Math.round(progress.recovery.recovery_rate * 100)}% recovered within ${progress.recovery.window_attempts} attempts`
                : 'Keep practicing to measure your recovery pattern.'}
            </h3>
            <p className="body-copy">
              {progress.recovery.sample_sufficient
                ? `${progress.recovery.recovery_count} of ${progress.recovery.eligible_mistakes} eligible mistakes were followed by a correct answer in the next ${progress.recovery.window_attempts} attempts${
                    progress.recovery.average_recovery_attempts == null
                      ? '.'
                      : `. Average attempts to the first correct answer: ${progress.recovery.average_recovery_attempts.toFixed(1)}.`
                  }`
                : `MISTIQ needs more complete post-mistake windows than the ${progress.recovery.eligible_mistakes} currently available.`}
            </p>
          </Card>
        )}

        {progress.stability && (
          <Card className="analytics-card">
            <div className="card-kicker">Learning stability</div>
            <h3>
              {{
                STABLE: 'Stable',
                IMPROVING: 'Improving',
                VARIABLE: 'Variable',
                NEEDS_MORE_DATA: 'Needs more data',
              }[progress.stability.status]}
            </h3>
            <p className="body-copy">
              {progress.stability.value == null
                ? 'The AMPA learning stability feature is not available yet.'
                : `Existing AMPA stability feature: ${Math.round(progress.stability.value * 100)}%. Based on ${progress.stability.sample_size} attempts.`}
            </p>
            {progress.mistake_momentum && (
              <>
                <p className="body-copy">
                  AMPA mistake-risk momentum: {progress.mistake_momentum.direction.toLowerCase().replace('_', ' ')}.
                </p>
                {progress.mistake_momentum.trend && (
                  <p className="body-copy">
                    Observed mistake frequency: {mistakeTrendText[progress.mistake_momentum.trend]}
                  </p>
                )}
              </>
            )}
          </Card>
        )}

        <Link className="text-link" to="/practice">
          Continue practicing <span aria-hidden="true">→</span>
        </Link>
      </div>
    </>
  )
}
