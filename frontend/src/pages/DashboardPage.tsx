import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { getProgress, getMistakes } from '../api/students'
import { getLatestPrediction, getLatestExplanation } from '../api/predictions'
import { getNextRecommendation } from '../api/recommendations'
import { getResearchEvaluation } from '../api/research'
import { mistakeLabels } from '../constants/errorLabels'
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components'
import type { MistakeEvent, Prediction, PredictionExplanation, Progress, RecommendedPractice } from '../types/entities'

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.'

function PredictionCard({
  prediction,
  explanation,
  empty = false,
}: {
  prediction: Prediction | null
  explanation: PredictionExplanation | null
  empty?: boolean
}) {
  if (!prediction) {
    return (
      <Card className="prediction-card">
        <div className="card-kicker">Likely next challenge</div>
        <div className="prediction-empty">
          <span className="illustration-mark" aria-hidden="true">✳</span>
          <div>
            <h3>{empty ? 'Keep practicing' : 'No challenge identified yet'}</h3>
            <p>We need a little more practice history before we can identify a likely challenge.</p>
          </div>
        </div>
      </Card>
    )
  }

  const reliable = prediction.status === 'NORMAL_OPERATION'

  return (
    <Card className="prediction-card">
      <div className="card-kicker">
        Likely next challenge{' '}
        <span className={reliable ? 'signal-pill' : 'signal-pill signal-early'}>
          {reliable ? 'Normal operation' : 'Early signal'}
        </span>
      </div>
      <div className="prediction-content">
        <span className="prediction-icon" aria-hidden="true">◉</span>
        <div>
          <h3>{mistakeLabels[prediction.prediction] || prediction.prediction.split('_').join(' ').toLowerCase()}</h3>
          <p>
            {reliable
              ? 'This estimate comes from the sequence of your recorded practice.'
              : 'This is an early signal from your practice so far. Keep exploring different questions.'}
          </p>
          {prediction.prediction === 'CONCEPT_CONFUSION' && explanation?.learning_need?.length ? (
            <p className="pattern-highlight">Recent concept confusion: {explanation.learning_need.join(', ')}</p>
          ) : null}
          {reliable && (
            <div className="prediction-metrics">
              <span>Model probability <strong>{(prediction.probability * 100).toFixed(0)}%</strong></span>
              <span>Confidence <strong>{(prediction.confidence * 100).toFixed(0)}%</strong></span>
              <span>Data reliability <strong>{(prediction.reliability * 100).toFixed(0)}%</strong></span>
            </div>
          )}
        </div>
      </div>
      {explanation && (
        <details className="prediction-why">
          <summary>Why am I seeing this?</summary>
          <p>{explanation.summary}</p>
          {explanation.evidence?.length > 0 && (
            <ul>
              {explanation.evidence.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          )}
          {explanation.top_predictions?.length > 0 && (
            <div className="top-probabilities">
              <strong>Other possible patterns</strong>
              {explanation.top_predictions.map(item => (
                <span key={item.error_type}>
                  {mistakeLabels[item.error_type]} · {(item.probability * 100).toFixed(0)}%
                </span>
              ))}
            </div>
          )}
        </details>
      )}
    </Card>
  )
}

function RecommendationCard({ recommendation }: { recommendation: RecommendedPractice | null }) {
  if (!recommendation) {
    return (
      <Card className="recommendation-card">
        <div className="card-kicker">Recommended practice</div>
        <h3>Practice questions will appear here</h3>
        <p>Add questions to the library to receive a next-step recommendation.</p>
      </Card>
    )
  }

  return (
    <Card className="recommendation-card">
      <div className="card-kicker">
        Recommended practice{' '}
        {recommendation.cold_start && <span className="signal-pill signal-early">Getting started</span>}
      </div>
      <h3>{recommendation.question.subtopic || recommendation.question.topic}</h3>
      <p>{recommendation.recommendation.reason}</p>
      <p className="recommendation-detail">
        Difficulty {recommendation.question.difficulty} of 5 · {recommendation.question.estimated_time} sec guide
      </p>
      <Link className="text-link" to={`/practice?question=${recommendation.question.question_id}`}>
        Try this question <span aria-hidden="true">→</span>
      </Link>
    </Card>
  )
}

function ModelPerformanceCard() {
  const [evaluation, setEvaluation] = useState<Record<string, any> | null>(null)

  useEffect(() => {
    let active = true
    getResearchEvaluation()
      .then(value => { if (active) setEvaluation(value) })
      .catch(() => undefined)
    return () => { active = false }
  }, [])

  const rows = Array.isArray(evaluation?.results) ? (evaluation.results as Record<string, any>[]) : []
  const mean = (name: string) => rows.find(row => row.model_name === name && String(row.seed) === 'mean')
  const ampa = mean('MISTIQ-AMPA')
  if (!ampa) return null
  const majority = mean('Majority')
  const percent = (value: unknown) => `${Math.round(Number(value) * 100)}%`

  return (
    <Card className="model-card">
      <div className="section-heading">
        <div>
          <div className="card-kicker">AMPA Engine Benchmark · Not Personal Score</div>
          <h3>How well MISTIQ predicts the next mistake</h3>
        </div>
        <Link to="/research" className="text-link">
          Research Lab <span aria-hidden="true">→</span>
        </Link>
      </div>
      <p className="body-copy">
        On an offline benchmark built from MISTIQ's synthetic practice data, the AMPA model predicts the next mistake category correctly {percent(ampa.accuracy)} of the time{majority ? `, compared with ${percent(majority.accuracy)} for always guessing the most common pattern` : ''}. Its predicted confidence is well calibrated, with {percent(ampa.ece)} expected calibration error.
      </p>
      <div className="research-facts">
        <span>Accuracy<strong>{percent(ampa.accuracy)}</strong></span>
        <span>Macro-F1<strong>{Number(ampa.macro_f1).toFixed(2)}</strong></span>
        <span>Calibration error<strong>{percent(ampa.ece)}</strong></span>
        <span>Majority baseline<strong>{majority ? percent(majority.accuracy) : '—'}</strong></span>
      </div>
      <p className="quiet-note">
        Measured offline on the synthetic benchmark used for evaluation, not from your live practice sessions.
      </p>
    </Card>
  )
}

export function DashboardPage() {
  const { student, user } = useStudent()
  const studentId = student?.id ?? user?.student_id ?? (typeof (user as any)?.id === 'number' ? (user as any).id : 0)

  const [progress, setProgress] = useState<Progress | null>(null)
  const [mistakes, setMistakes] = useState<MistakeEvent[]>([])
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [explanation, setExplanation] = useState<PredictionExplanation | null>(null)
  const [recommendation, setRecommendation] = useState<RecommendedPractice | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!studentId) return
    let active = true

    Promise.all([
      getProgress(studentId),
      getMistakes(studentId),
      getLatestPrediction(studentId).catch(() => null),
      getNextRecommendation(studentId).catch(() => null),
    ])
      .then(([nextProgress, nextMistakes, nextPrediction, nextRecommendation]) => {
        if (active) {
          setProgress(nextProgress)
          setMistakes(nextMistakes)
          setPrediction(nextPrediction)
          setRecommendation(nextRecommendation)
        }
      })
      .catch(reason => {
        if (active) setError(errorMessage(reason))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [studentId])

  useEffect(() => {
    if (!studentId || !prediction) return
    let active = true
    getLatestExplanation(studentId)
      .then(value => { if (active) setExplanation(value) })
      .catch(() => undefined)
    return () => { active = false }
  }, [studentId, prediction?.id])

  if (loading) {
    return (
      <>
        <PageHeader title="Your dashboard" description="A little progress, one question at a time." />
        <LoadingState label="Loading your learning summary…" />
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageHeader title="Your dashboard" description="A little progress, one question at a time." />
        <ErrorState message={error} />
      </>
    )
  }

  const rawName = student?.name || user?.name || user?.username || 'Learner'
  const firstName = rawName.split(' ')[0]
  const recent = mistakes.slice(-3).reverse()

  return (
    <>
      <PageHeader
        title={`Good to see you, ${firstName}.`}
        description="Small steps add up. Pick up where you left off."
      />
      <div className="dashboard-grid">
        {/* Welcome Card & Primary Action */}
        <Card className="welcome-card">
          <div className="welcome-content">
            <span className="eyebrow">Your next step</span>
            <h2>Make a little progress today.</h2>
            <p>Work through a question at your own pace. Your learning history will help MISTIQ show useful patterns over time.</p>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginTop: '16px' }}>
              <Link className="button" to="/practice">
                Start practicing <span aria-hidden="true">→</span>
              </Link>
              {studentId > 0 && (
                <span className="badge badge-accent">
                  Profile: {rawName} (ID #{studentId})
                </span>
              )}
            </div>
          </div>
          <div className="welcome-decoration" aria-hidden="true">✳</div>
        </Card>

        {/* 1. Student Personal Progress Card */}
        <Card className="summary-card">
          <div className="section-heading">
            <div>
              <div className="card-kicker">Your progress</div>
              <h3>A steady start</h3>
            </div>
            <Link to="/progress" className="text-link">
              View progress <span aria-hidden="true">→</span>
            </Link>
          </div>
          {!progress?.attempt_count ? (
            <EmptyState
              title="Your first session starts here"
              description="Your progress summary will take shape as you practice."
            >
              <Link className="button button-secondary" to="/practice">
                Take First 5-Question Quiz <span aria-hidden="true">→</span>
              </Link>
            </EmptyState>
          ) : (
            <>
              <div className="stat-row">
                <div>
                  <strong>{progress.attempt_count}</strong>
                  <span>Questions tried</span>
                </div>
                <div>
                  <strong>{Math.round(progress.accuracy * 100)}<small>%</small></strong>
                  <span>Accuracy</span>
                </div>
                <div>
                  <strong>{progress.mistake_count}</strong>
                  <span>Things to review</span>
                </div>
              </div>
              <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--muted)' }}>
                <span>Correct answers: <strong>{progress.correct_count}</strong></span>
                <span>Current streak: <strong>{progress.summary?.current_streak ?? 0}</strong></span>
                <span>Topics practiced: <strong>{progress.summary?.topics_practiced ?? progress.topic_performance?.length ?? 1}</strong></span>
              </div>
            </>
          )}
        </Card>

        {/* 2. Likely Next Challenge Card */}
        <PredictionCard prediction={prediction} explanation={explanation} empty={!progress?.attempt_count} />

        {/* 3. Recommended Practice Card */}
        <RecommendationCard recommendation={recommendation} />

        {/* 4. Recent Mistakes Card */}
        <Card className="recent-card">
          <div className="section-heading">
            <div>
              <div className="card-kicker">Recent learning</div>
              <h3>Mistakes are useful clues</h3>
            </div>
            <Link to="/mistakes" className="text-link">
              Review all <span aria-hidden="true">→</span>
            </Link>
          </div>
          {recent.length ? (
            <ul className="compact-list">
              {recent.map(item => (
                <li key={item.mistake_event_id}>
                  <span className="list-dot" aria-hidden="true" />
                  <span>
                    <strong>{mistakeLabels[item.error_type]}</strong>
                    <small>{item.topic}{item.subtopic ? ` · ${item.subtopic}` : ''}</small>
                  </span>
                  <time>{new Date(item.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</time>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="A clean slate"
              description="Your recent review topics will show up here after a practice session."
            />
          )}
        </Card>

        {/* 5. Offline Model Benchmark (Explicitly labeled as Research Benchmark) */}
        <ModelPerformanceCard />
      </div>
    </>
  )
}
