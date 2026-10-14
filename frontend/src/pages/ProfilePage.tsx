import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { getLearnerState } from '../api/students'
import { ApiError } from '../api/client'
import { Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components'
import type { LearnerState } from '../types/entities'

type LearnerSignal = 'concept_confusion' | 'knowledge_stability' | 'difficulty_sensitivity' | 'mistake_momentum'

const profileMeasures: Array<{ label: string; key: LearnerSignal; inverse?: boolean; description: string }> = [
  {
    label: 'Concept confidence',
    key: 'concept_confusion',
    inverse: true,
    description: 'Estimated from concept-confusion events in your recorded history.',
  },
  {
    label: 'Learning stability',
    key: 'knowledge_stability',
    description: 'Calculated from correctness and outcome consistency across your recorded attempts.',
  },
  {
    label: 'Challenge handling',
    key: 'difficulty_sensitivity',
    inverse: true,
    description: 'Estimated from how mistake patterns vary by question difficulty.',
  },
  {
    label: 'Practice rhythm',
    key: 'mistake_momentum',
    inverse: true,
    description: 'Estimated from the pattern of recent attempts.',
  },
]

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.'

export function ProfilePage() {
  const { student, user } = useStudent()
  const studentId = student?.id ?? user?.student_id ?? (typeof (user as any)?.id === 'number' ? (user as any).id : 0)

  const [state, setState] = useState<LearnerState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!studentId) return
    let active = true

    getLearnerState(studentId)
      .then(value => { if (active) setState(value) })
      .catch(reason => {
        if (!(reason instanceof ApiError && reason.status === 409)) {
          if (active) setError(errorMessage(reason))
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [studentId])

  if (loading) {
    return (
      <>
        <PageHeader
          title="Your learning profile"
          description="A gentle snapshot of patterns in your practice. These are learning signals, not labels."
        />
        <LoadingState label="Reading your learning history…" />
      </>
    )
  }

  if (error) {
    return (
      <>
        <PageHeader
          title="Your learning profile"
          description="A gentle snapshot of patterns in your practice. These are learning signals, not labels."
        />
        <ErrorState message={error} />
      </>
    )
  }

  if (!state) {
    return (
      <>
        <PageHeader
          title="Your learning profile"
          description="A gentle snapshot of patterns in your practice. These are learning signals, not labels."
        />
        <Card>
          <EmptyState
            title="Your profile will grow with practice"
            description="Start with a few questions. MISTIQ will build a profile from your actual learning history."
          >
            <Link className="button" to="/practice">
              Start practicing <span aria-hidden="true">→</span>
            </Link>
          </EmptyState>
        </Card>
      </>
    )
  }

  const displayName = student?.name || user?.name || user?.username || 'Learner'
  const initial = displayName.slice(0, 1).toUpperCase()

  return (
    <>
      <PageHeader
        title="Your learning profile"
        description="A gentle snapshot of patterns in your practice. These are learning signals, not labels."
      />

      <Card className="profile-intro">
        <div className="avatar avatar-large" aria-hidden="true">{initial}</div>
        <div>
          <div className="card-kicker">LEARNING PROFILE</div>
          <h2>{displayName}</h2>
          <p>{state.attempt_count} attempts · {state.relevant_mistake_count} review moments</p>
        </div>
      </Card>

      <div className="profile-measures">
        {profileMeasures.map(measure => {
          const raw = state[measure.key]
          const score = Math.round(Math.max(0, Math.min(1, measure.inverse ? 1 - raw : raw)) * 100)
          return (
            <Card key={measure.key}>
              <div className="measure-heading">
                <h3>{measure.label}</h3>
                <strong>{score}%</strong>
              </div>
              <div
                className="measure-track"
                role="progressbar"
                aria-label={measure.label}
                aria-valuenow={score}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <span style={{ width: `${score}%` }} />
              </div>
              <p>{measure.description}</p>
            </Card>
          )
        })}
      </div>

      <p className="quiet-note" style={{ marginTop: '20px' }}>
        These are computational learning-history signals, not psychological or permanent labels. They adapt continuously as you practice.
      </p>
    </>
  )
}
