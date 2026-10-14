import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { getQuestions } from '../api/questions'
import { submitAttempt } from '../api/attempts'
import { mistakeLabels } from '../constants/errorLabels'
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components'
import type { AttemptSubmission, OptionKey, Question } from '../types/entities'

const optionKeys: OptionKey[] = ['A', 'B', 'C', 'D']
const optionText = (question: Question, key: OptionKey) =>
  question[`option_${key.toLowerCase()}` as 'option_a' | 'option_b' | 'option_c' | 'option_d']

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.'

interface SessionRecord {
  question: Question
  selectedOption: OptionKey
  correct: boolean
  correctOption: OptionKey
  correctAnswer: string
  mistakeType: string | null
  responseTime: number
}

export function PracticePage() {
  const { student, user } = useStudent()
  const studentId = student?.id ?? user?.student_id ?? (typeof (user as any)?.id === 'number' ? (user as any).id : 0)
  const location = useLocation()
  const navigate = useNavigate()

  const [allQuestions, setAllQuestions] = useState<Question[]>([])
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<OptionKey | null>(null)
  const [result, setResult] = useState<AttemptSubmission | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [startedAt, setStartedAt] = useState(Date.now())
  const feedbackRef = useRef<HTMLDivElement>(null)

  // Session state
  const [sessionLength, setSessionLength] = useState<number>(5)
  const [sessionHistory, setSessionHistory] = useState<SessionRecord[]>([])
  const [sessionFinished, setSessionFinished] = useState(false)
  const [sessionStartTime] = useState(Date.now())

  useEffect(() => {
    let active = true
    const params = new URLSearchParams(location.search)
    const topic = params.get('topic') || undefined
    const subtopic = params.get('subtopic') || undefined
    const requestedQuestionId = Number(params.get('question'))

    getQuestions({ topic, subtopic })
      .then(items => {
        if (!active) return
        setAllQuestions(items)
        if (requestedQuestionId) {
          const matchIndex = items.findIndex(q => q.question_id === requestedQuestionId)
          if (matchIndex >= 0) {
            setIndex(matchIndex)
            setSessionLength(1)
          }
        } else {
          setSessionLength(Math.min(5, Math.max(1, items.length)))
        }
      })
      .catch(reason => {
        if (active) setError(errorMessage(reason))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [location.search])

  const questions = useMemo(() => {
    return allQuestions.slice(0, sessionLength > 0 ? sessionLength : allQuestions.length)
  }, [allQuestions, sessionLength])

  const question = questions[index]

  useEffect(() => {
    if (question && !result) {
      setStartedAt(Date.now())
    }
  }, [question?.question_id, result])

  useEffect(() => {
    if (result) {
      feedbackRef.current?.focus({ preventScroll: true })
    }
  }, [result])

  const submit = useCallback(async () => {
    if (!studentId || !question || !selected || submitting) return
    setSubmitting(true)
    setError('')
    const responseSeconds = Math.max(1, Math.round((Date.now() - startedAt) / 1000))
    try {
      const response = await submitAttempt({
        student_id: studentId,
        question_id: question.question_id,
        selected_option: selected,
        response_time: responseSeconds,
        idempotency_key: crypto.randomUUID(),
      })
      setResult(response)

      // Add to session records
      setSessionHistory(prev => [
        ...prev,
        {
          question,
          selectedOption: selected,
          correct: response.attempt.correct,
          correctOption: response.correct_option,
          correctAnswer: response.correct_answer,
          mistakeType: response.mistake_event?.error_type ?? null,
          responseTime: responseSeconds,
        },
      ])
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setSubmitting(false)
    }
  }, [studentId, question, selected, submitting, startedAt])

  const nextQuestion = useCallback(() => {
    if (index + 1 >= questions.length) {
      setSessionFinished(true)
      return
    }
    setIndex(current => current + 1)
    setSelected(null)
    setResult(null)
    setError('')
    setStartedAt(Date.now())
  }, [index, questions.length])

  const restartSession = useCallback(() => {
    setSessionHistory([])
    setSessionFinished(false)
    setIndex(0)
    setSelected(null)
    setResult(null)
    setError('')
    setStartedAt(Date.now())
  }, [])

  // Keyboard navigation support: 1/2/3/4 or A/B/C/D to pick, Enter to submit
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (sessionFinished) return
      if (result) {
        if (e.key === 'Enter') {
          e.preventDefault()
          nextQuestion()
        }
        return
      }
      if (['1', 'a', 'A'].includes(e.key)) {
        setSelected('A')
      } else if (['2', 'b', 'B'].includes(e.key)) {
        setSelected('B')
      } else if (['3', 'c', 'C'].includes(e.key)) {
        setSelected('C')
      } else if (['4', 'd', 'D'].includes(e.key)) {
        setSelected('D')
      } else if (e.key === 'Enter' && selected && !submitting) {
        e.preventDefault()
        void submit()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [result, selected, submitting, nextQuestion, submit, sessionFinished])

  if (loading) {
    return (
      <>
        <PageHeader title="Practice" description="Take your time. Each question is a chance to learn." />
        <LoadingState label="Finding a question…" />
      </>
    )
  }

  if (error && !question) {
    return (
      <>
        <PageHeader title="Practice" description="Take your time. Each question is a chance to learn." />
        <ErrorState message={error} />
      </>
    )
  }

  if (!questions.length) {
    return (
      <>
        <PageHeader title="Practice" description="Take your time. Each question is a chance to learn." />
        <Card>
          <EmptyState
            title="No questions are available yet"
            description="Once questions are added to the learning library, they will appear here."
          />
        </Card>
      </>
    )
  }

  // =========================================================================
  // QUIZ COMPLETED / MARKS SUMMARY SCREEN
  // =========================================================================
  if (sessionFinished && sessionHistory.length > 0) {
    const totalAnswered = sessionHistory.length
    const totalCorrect = sessionHistory.filter(r => r.correct).length
    const totalMistakes = totalAnswered - totalCorrect
    const percentage = Math.round((totalCorrect / totalAnswered) * 100)
    const totalTimeSeconds = Math.round((Date.now() - sessionStartTime) / 1000)
    const minutes = Math.floor(totalTimeSeconds / 60)
    const seconds = totalTimeSeconds % 60
    const timeFormatted = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`

    let ratingBadge = { label: 'Good Effort · Review Needed', color: 'badge-warning', tip: 'Mistakes are learning clues. Review the concepts below.' }
    if (percentage === 100) {
      ratingBadge = { label: 'Flawless Mastery! 🎉', color: 'badge-success', tip: 'Perfect accuracy. AMPA recorded high knowledge stability.' }
    } else if (percentage >= 80) {
      ratingBadge = { label: 'Great Work! 🌟', color: 'badge-success', tip: 'Strong conceptual clarity with minor review points.' }
    } else if (percentage >= 60) {
      ratingBadge = { label: 'Solid Progress 📚', color: 'badge-accent', tip: 'Good attempt. Targeted practice on missed concepts will solidify understanding.' }
    }

    return (
      <div className="quiz-results-view">
        <PageHeader
          title="Quiz Complete · Marks Summary"
          description="Your attempt sequence has been processed by MISTIQ-AMPA. Here is your performance breakdown."
        />

        <div className="results-grid">
          {/* Main Marks Banner */}
          <Card className="marks-banner-card">
            <div className="marks-header">
              <span className={`badge ${ratingBadge.color}`}>{ratingBadge.label}</span>
              <span className="marks-time">Time spent: {timeFormatted}</span>
            </div>

            <div className="marks-display">
              <div className="marks-score-circle">
                <strong className="marks-number">{percentage}%</strong>
                <span>Accuracy</span>
              </div>
              <div className="marks-breakdown">
                <h2>{totalCorrect} of {totalAnswered} Correct</h2>
                <p className="marks-tip">{ratingBadge.tip}</p>
                <div className="marks-pill-row">
                  <span className="marks-stat-pill pill-correct">
                    ✓ {totalCorrect} Correct ({percentage} marks)
                  </span>
                  <span className="marks-stat-pill pill-review">
                    ↳ {totalMistakes} Review Moments
                  </span>
                  <span className="marks-stat-pill pill-pace">
                    ⏱ Avg {Math.round(totalTimeSeconds / totalAnswered)}s / question
                  </span>
                </div>
              </div>
            </div>

            <div className="marks-actions">
              <Button onClick={() => navigate('/dashboard')}>
                View Updated Dashboard <span aria-hidden="true">→</span>
              </Button>
              <Button className="button-secondary" onClick={restartSession}>
                Practice Another Quiz Session
              </Button>
              <Link className="text-link" to="/mistakes" style={{ marginLeft: 'auto' }}>
                Review Mistakes Hub <span aria-hidden="true">→</span>
              </Link>
            </div>
          </Card>

          {/* AMPA Intelligence Insight Card */}
          <Card className="ampa-update-card">
            <div className="card-kicker">MISTIQ-AMPA Live Update</div>
            <h3>Sequential Model Adaptation</h3>
            <p className="body-copy">
              {totalMistakes === 0
                ? 'Your sequential mistake momentum remained at zero. Learning stability was reinforced across the attempted topics.'
                : `AMPA identified ${totalMistakes} mistake event${totalMistakes > 1 ? 's' : ''} in this sequence. Distractor patterns and recency weights have been recalculated to adapt your next recommendation.`}
            </p>
          </Card>

          {/* Question by Question Detailed Marks Review */}
          <Card className="question-review-card">
            <div className="section-heading">
              <div>
                <div className="card-kicker">Detailed Breakdown</div>
                <h3>Question-by-Question Review</h3>
              </div>
              <span className="badge">{totalAnswered} Questions Reviewed</span>
            </div>

            <div className="review-list">
              {sessionHistory.map((rec, i) => (
                <div
                  key={rec.question.question_id}
                  className={`review-item ${rec.correct ? 'review-item-correct' : 'review-item-incorrect'}`}
                >
                  <div className="review-item-header">
                    <span className="review-q-num">Q{i + 1}</span>
                    <span className="crumb">{rec.question.topic}{rec.question.subtopic ? ` · ${rec.question.subtopic}` : ''}</span>
                    <span className={`review-status-tag ${rec.correct ? 'tag-correct' : 'tag-incorrect'}`}>
                      {rec.correct ? '✓ Correct' : '✗ Incorrect'}
                    </span>
                  </div>

                  <p className="review-question-text">{rec.question.question_text}</p>

                  <div className="review-answers-box">
                    <div className="review-user-answer">
                      <span>Your choice:</span>
                      <strong>
                        Option {rec.selectedOption}: {optionText(rec.question, rec.selectedOption)}
                      </strong>
                    </div>

                    {!rec.correct && (
                      <div className="review-correct-answer">
                        <span>Correct answer:</span>
                        <strong>
                          Option {rec.correctOption}: {rec.correctAnswer}
                        </strong>
                      </div>
                    )}
                  </div>

                  {rec.mistakeType && (
                    <div className="review-mistake-note">
                      <span className="badge badge-warning">
                        Pattern: {mistakeLabels[rec.mistakeType as keyof typeof mistakeLabels] || rec.mistakeType}
                      </span>
                      {rec.mistakeType === 'CONCEPT_CONFUSION' && (
                        <span className="review-subnote">
                          Concept distinction: {rec.question.subtopic || rec.question.topic} ↔ {optionText(rec.question, rec.selectedOption)}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    )
  }

  // =========================================================================
  // ACTIVE QUESTION SCREEN
  // =========================================================================
  const difficultyLabels = ['Very easy', 'Easy', 'Medium', 'Hard', 'Very hard']
  const difficulty = difficultyLabels[question.difficulty - 1] || 'Medium'
  const isLastQuestion = index + 1 >= questions.length
  const answeredCount = sessionHistory.length
  const correctCount = sessionHistory.filter(r => r.correct).length

  return (
    <>
      <PageHeader
        title="Practice Session"
        description="Take your time. Each question is analyzed chronologically by MISTIQ."
      />

      {/* Session Progress Header */}
      <div className="quiz-session-header">
        <div className="session-tracker">
          <div className="session-progress-info">
            <span className="session-q-counter">
              Question <strong>{index + 1}</strong> of <strong>{questions.length}</strong>
            </span>
            {answeredCount > 0 && (
              <span className="session-live-score">
                Current score: <strong>{correctCount} / {answeredCount}</strong> correct
              </span>
            )}
          </div>
          <div className="session-bar-track">
            <span
              className="session-bar-fill"
              style={{ width: `${Math.round(((index + (result ? 1 : 0)) / questions.length) * 100)}%` }}
            />
          </div>
        </div>
      </div>

      <div className="practice-layout">
        <div className="practice-main">
          <div className="practice-meta">
            <span className="crumb">{question.topic}{question.subtopic ? ` / ${question.subtopic}` : ''}</span>
            <span className="badge badge-accent difficulty-tag">Difficulty {question.difficulty} · {difficulty}</span>
          </div>

          <Card className="question-card">
            <div className="question-count">
              QUESTION {String(index + 1).padStart(2, '0')} <span>·</span> {question.estimated_time} sec guide
            </div>
            <h2>{question.question_text}</h2>

            <fieldset className="answer-list" disabled={!!result || submitting}>
              <legend className="sr-only">Choose one answer</legend>
              {optionKeys.map(key => {
                const isSelected = selected === key
                const isCorrect = result?.correct_option === key
                const isIncorrectSelection = result && isSelected && !result.attempt.correct
                return (
                  <label
                    key={key}
                    className={`answer-option ${isSelected ? 'selected' : ''} ${isCorrect ? 'answer-correct' : ''} ${isIncorrectSelection ? 'answer-incorrect' : ''}`}
                  >
                    <input
                      type="radio"
                      name="answer"
                      value={key}
                      aria-label={`${key}. ${optionText(question, key)}`}
                      checked={isSelected}
                      onChange={() => setSelected(key)}
                    />
                    <span className="option-key" aria-hidden="true">{key}</span>
                    <span className="option-text">{optionText(question, key)}</span>
                    {isCorrect && <span className="answer-mark">Correct answer</span>}
                  </label>
                )
              })}
            </fieldset>

            {error && <ErrorState message={error} />}

            {!result ? (
              <div className="question-actions">
                <span className="quiet-note">
                  Press 1-4 or A-D to select, Enter to check answer.
                </span>
                <Button onClick={submit} disabled={!selected || submitting}>
                  {submitting ? 'Checking…' : 'Submit answer'} <span aria-hidden="true">→</span>
                </Button>
              </div>
            ) : (
              <div
                ref={feedbackRef}
                tabIndex={-1}
                className={`feedback-panel ${result.attempt.correct ? 'feedback-good' : 'feedback-review'}`}
                role="status"
              >
                <span className="feedback-icon" aria-hidden="true">
                  {result.attempt.correct ? '✓' : '↳'}
                </span>
                <div>
                  <h3>{result.attempt.correct ? 'Correct.' : 'Not quite.'}</h3>
                  <p>
                    The correct answer is <strong>{result.correct_option}. {result.correct_answer}</strong>
                  </p>

                  {result.mistake_event?.error_type === 'CONCEPT_CONFUSION' && (
                    <div className="aha-card">
                      <div className="card-kicker">A pattern MISTIQ noticed</div>
                      <strong>Concept confusion</strong>
                      <p className="confusion-pair">
                        {question.subtopic || question.topic} ↔ {optionText(question, result.attempt.selected_option)}
                      </p>
                      <p>Your answer connects two related concepts. Practicing this distinction can help make the difference clearer.</p>
                      <Link className="button button-secondary" to={`/practice?topic=${encodeURIComponent(question.topic)}`}>
                        Practice this concept
                      </Link>
                    </div>
                  )}

                  {result.mistake_event && (
                    <p>
                      This looks like a <strong>{mistakeLabels[result.mistake_event.error_type]?.toLowerCase()}</strong> in {result.mistake_event.subtopic || result.mistake_event.topic}. A good concept to revisit.
                    </p>
                  )}

                  {!result.mistake_event && (
                    <p>Keep building on what you know about {question.subtopic || question.topic}.</p>
                  )}

                  {result.prediction && (
                    <p className="feedback-prediction">
                      A possible next challenge: {mistakeLabels[result.prediction.prediction]?.toLowerCase() || result.prediction.prediction}.
                    </p>
                  )}

                  {!result.prediction && (
                    <p className="quiet-note">
                      {result.prediction_status === 'NO_RELIABLE_PREDICTION'
                        ? 'A few more practice answers will help MISTIQ spot useful patterns.'
                        : 'Your attempt and learning progress have been saved.'}
                    </p>
                  )}

                  <div style={{ display: 'flex', gap: '10px', marginTop: '14px', alignItems: 'center' }}>
                    <Button className="button-secondary" onClick={nextQuestion}>
                      {isLastQuestion ? 'Complete Quiz & View Marks' : 'Next question'} <span aria-hidden="true">→</span>
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>

        <aside className="practice-aside">
          <Card>
            <span className="aside-mark" aria-hidden="true">✳</span>
            <h3>Quiz Session</h3>
            <p>Give each question a thoughtful try. After completing this session, your marks and sequential insights will be presented.</p>
            <div className="aside-rule" />
            <span className="aside-label">IN THIS QUIZ</span>
            <strong>{questions.length} questions total</strong>
            <div style={{ marginTop: '12px' }}>
              <span className="aside-label">ANSWERED SO FAR</span>
              <strong>{answeredCount} of {questions.length}</strong>
            </div>
          </Card>
        </aside>
      </div>
    </>
  )
}
