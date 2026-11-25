import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { getProgress, getMistakes } from '../api/students'
import { getLatestPrediction, getLatestExplanation } from '../api/predictions'
import { getNextRecommendation } from '../api/recommendations'
import { mistakeLabels } from '../constants/errorLabels'
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components'
import type { MistakeEvent, Prediction, PredictionExplanation, Progress, RecommendedPractice } from '../types/entities'

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.'

function PredictionCard({
  prediction,
  explanation,
  empty,
}: {
  prediction: Prediction | null
  explanation: PredictionExplanation | null
  empty?: boolean
}) {
  if (!prediction) {
    return (
      <Card className="prediction-card">
        <div className="card-kicker">Recommended Study Focus</div>
        <div className="prediction-empty">
          <span className="illustration-mark" aria-hidden="true">✳</span>
          <div>
            <h3>{empty ? 'Keep practicing' : 'No challenge identified yet'}</h3>
            <p>Complete a quick quiz to receive personalized topic recommendations based on your responses.</p>
          </div>
        </div>
      </Card>
    )
  }

  const reliable = prediction.status === 'NORMAL_OPERATION'
  const conceptName = explanation?.learning_need?.[0] || 'Precision'

  return (
    <Card className="prediction-card">
      <div className="card-kicker">
        Personalized Study Focus{' '}
        <span className="signal-pill">Adaptive Recommendation</span>
      </div>
      <div className="prediction-content">
        <span className="prediction-icon" aria-hidden="true">◉</span>
        <div>
          <h3>{mistakeLabels[prediction.prediction] || prediction.prediction.split('_').join(' ').toLowerCase()}</h3>
          <p>
            Based on your recent practice history, focusing on this topic will help reinforce your understanding and avoid common exam traps.
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
          <div style={{ display: 'flex', gap: '10px', marginTop: '12px', flexWrap: 'wrap' }}>
            <Link className="button button-secondary" to={`/practice?topic=${encodeURIComponent(conceptName)}&mode=learn`}>
              📖 Study {conceptName} Notes
            </Link>
            <Link className="button" to={`/practice?topic=${encodeURIComponent(conceptName)}&mode=quiz`}>
              🎯 Practice {conceptName}
            </Link>
          </div>
        </div>
      </div>
      {explanation && (
        <details className="prediction-why" style={{ marginTop: '14px' }}>
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
      <div style={{ display: 'flex', gap: '10px', marginTop: '12px', flexWrap: 'wrap' }}>
        <Link className="button button-secondary" to={`/practice?topic=${encodeURIComponent(recommendation.question.topic)}&mode=learn`}>
          📖 Study Concept Guide
        </Link>
        <Link
          className="button"
          to={`/practice?question=${recommendation.question.question_id}`}
          aria-label="Try this question"
        >
          🎯 Try this question →
        </Link>
      </div>
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
    if (!studentId) return
    let active = true

    getLatestExplanation(studentId)
      .then(nextExplanation => {
        if (active) setExplanation(nextExplanation)
      })
      .catch(() => {
        if (active) setExplanation(null)
      })

    return () => { active = false }
  }, [studentId, prediction?.id])

  if (loading) {
    return (
      <>
        <PageHeader title="Your dashboard" description="Loading your personalized learning path…" />
        <LoadingState label="Preparing your dashboard…" />
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
        description="Pick up where you left off and strengthen your concept mastery."
      />
      <div className="dashboard-grid">
        {/* Welcome Card & Primary Action */}
        <Card className="welcome-card">
          <div className="welcome-content">
            <span className="eyebrow">Your Daily Practice</span>
            <h2>Continue your learning path today.</h2>
            <p>Consistent, targeted problem-solving builds conceptual clarity. Work through lessons at your own pace.</p>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap' }}>
              <Link className="button" to="/practice">
                Start Practicing <span aria-hidden="true">→</span>
              </Link>
              <Link className="button button-secondary" to="/practice?mode=learn">
                Browse Concept Guides 📖
              </Link>
            </div>
          </div>
          <div className="welcome-decoration" aria-hidden="true">✳</div>
        </Card>

        {/* 1. Student Personal Progress Card */}
        <Card className="summary-card">
          <div className="section-heading">
            <div>
              <div className="card-kicker">Your Learning Stats</div>
              <h3>Current Progress</h3>
            </div>
            <Link to="/progress" className="text-link">
              View full progress <span aria-hidden="true">→</span>
            </Link>
          </div>
          {!progress?.attempt_count ? (
            <EmptyState
              title="Your learning journey begins here"
              description="Complete your first practice quiz to generate personalized mastery metrics."
            >
              <Link className="button button-secondary" to="/practice">
                Take First Practice Quiz <span aria-hidden="true">→</span>
              </Link>
            </EmptyState>
          ) : (
            <>
              <div className="stat-row">
                <div>
                  <strong>{progress.attempt_count}</strong>
                  <span>Questions Solved</span>
                </div>
                <div>
                  <strong>{Math.round(progress.accuracy * 100)}<small>%</small></strong>
                  <span>Accuracy</span>
                </div>
                <div>
                  <strong>{progress.mistake_count}</strong>
                  <span>Items to Review</span>
                </div>
              </div>
              <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--muted)' }}>
                <span>Correct answers: <strong>{progress.correct_count}</strong></span>
                <span>Active streak: <strong>{progress.summary?.current_streak ?? 0} days</strong></span>
                <span>Topics covered: <strong>{progress.summary?.topics_practiced ?? progress.topic_performance?.length ?? 1}</strong></span>
              </div>
            </>
          )}
        </Card>

        {/* 2. Personalized Study Focus Card */}
        <PredictionCard prediction={prediction} explanation={explanation} empty={!progress?.attempt_count} />

        {/* 3. Recommended Practice Card */}
        <RecommendationCard recommendation={recommendation} />

        {/* 4. Review Items Card */}
        <Card className="recent-card">
          <div className="section-heading">
            <div>
              <div className="card-kicker">Review Center</div>
              <h3>Recent Misconceptions</h3>
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
              title="All clear"
              description="Any concepts you find tricky during practice will appear here for easy review."
            />
          )}
        </Card>
      </div>
    </>
  )
}
