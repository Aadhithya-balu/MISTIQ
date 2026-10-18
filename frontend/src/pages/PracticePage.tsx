import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { getQuestions } from '../api/questions'
import { submitAttempt } from '../api/attempts'
import { mistakeLabels } from '../constants/errorLabels'
import { CONCEPT_GUIDES, getConceptGuide, type ConceptGuide } from '../constants/concepts'
import { Button, Card, EmptyState, ErrorState, Icon, LoadingState, PageHeader } from '../components'
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

  // Mode: 'learn' (Concept Teaching) or 'quiz' (Interactive Testing)
  const [activeTab, setActiveTab] = useState<'learn' | 'quiz'>('learn')
  const [selectedConceptId, setSelectedConceptId] = useState<string>('Precision')
  const [showInQuizHint, setShowInQuizHint] = useState<boolean>(false)

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
    const modeParam = params.get('mode')
    const topicParam = params.get('topic') || undefined
    const subtopicParam = params.get('subtopic') || undefined
    const requestedQuestionId = Number(params.get('question'))

    if (modeParam === 'learn') {
      setActiveTab('learn')
    } else if (modeParam === 'quiz' || requestedQuestionId) {
      setActiveTab('quiz')
    }

    if (topicParam) {
      setSelectedConceptId(topicParam)
    }

    getQuestions({ topic: topicParam, subtopic: subtopicParam })
      .then(items => {
        if (!active) return
        setAllQuestions(items)
        if (requestedQuestionId) {
          const matchIndex = items.findIndex(q => q.question_id === requestedQuestionId)
          if (matchIndex >= 0) {
            setIndex(matchIndex)
            setSessionLength(1)
            if (items[matchIndex]?.topic) {
              setSelectedConceptId(items[matchIndex].topic)
            }
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

  // Update selected concept guide if question changes
  useEffect(() => {
    if (question?.topic && CONCEPT_GUIDES[question.topic]) {
      setSelectedConceptId(question.topic)
    }
  }, [question?.topic])

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
    setShowInQuizHint(false)
    setStartedAt(Date.now())
  }, [index, questions.length])

  // Keyboard navigation support: 1/2/3/4 or A/B/C/D to pick, Enter to submit
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (activeTab !== 'quiz' || sessionFinished) return
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
  }, [activeTab, result, selected, submitting, nextQuestion, submit, sessionFinished])

  const activeGuide: ConceptGuide = getConceptGuide(selectedConceptId)

  const startQuizForConcept = (topic: string) => {
    const matchIndex = allQuestions.findIndex(q => q.topic.toLowerCase() === topic.toLowerCase())
    if (matchIndex >= 0) {
      setIndex(matchIndex)
      setSelected(null)
      setResult(null)
    }
    setActiveTab('quiz')
  }

  return (
    <div className="practice-page-container">
      <PageHeader
        title="Learning & Practice Hub"
        description="Master core concepts through interactive mental models, then validate your understanding with MISTIQ-AMPA adaptive testing."
      />

      {/* Top Mode Selector Tabs */}
      <div className="practice-mode-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'learn'}
          className={`mode-tab-button ${activeTab === 'learn' ? 'active' : ''}`}
          onClick={() => setActiveTab('learn')}
        >
          <Icon name="book" />
          <span>📖 Learn Concepts & Theory</span>
          <span className="mode-tab-pill">Self-Paced Guide</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'quiz'}
          className={`mode-tab-button ${activeTab === 'quiz' ? 'active' : ''}`}
          onClick={() => setActiveTab('quiz')}
        >
          <Icon name="practice" />
          <span>🎯 Practice & Knowledge Test</span>
          <span className="mode-tab-pill">AMPA Tracked</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* VIEW 1: CONCEPT TEACHING & INTUITION GUIDE */}
      {/* ========================================================================= */}
      {activeTab === 'learn' && (
        <div className="concept-teaching-view">
          {/* Concept Topic Selector Pills */}
          <div className="concept-selector-bar">
            <span className="selector-label">Curriculum Topics:</span>
            <div className="concept-pills-list">
              {Object.keys(CONCEPT_GUIDES).map(key => {
                const guide = CONCEPT_GUIDES[key]
                const isCurrent = guide.id === activeGuide.id
                return (
                  <button
                    key={guide.id}
                    type="button"
                    className={`concept-pill ${isCurrent ? 'active' : ''}`}
                    onClick={() => setSelectedConceptId(guide.id)}
                  >
                    {guide.title}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="concept-layout">
            <div className="concept-main-content">
              {/* Concept Hero Header Card */}
              <Card className="concept-hero-card">
                <div className="concept-header-meta">
                  <span className="badge badge-accent">{activeGuide.category}</span>
                  <span className="concept-reading-time">⏱ ~3 min read</span>
                </div>
                <h2>{activeGuide.title}</h2>
                <p className="concept-lead-summary">{activeGuide.summary}</p>

                <div className="core-question-callout">
                  <span className="core-q-label">Core Question to Ask:</span>
                  <strong>"{activeGuide.coreQuestion}"</strong>
                </div>

                {activeGuide.formulaOrRule && (
                  <div className="concept-formula-box">
                    <span className="formula-tag">Mathematical Rule / Definition:</span>
                    <code>{activeGuide.formulaOrRule}</code>
                  </div>
                )}
              </Card>

              {/* Side-by-Side Comparison Matrix */}
              <Card className="concept-comparison-card">
                <div className="card-kicker">Side-by-Side Mental Model</div>
                <h3>Differentiating the Two Concepts</h3>
                <p className="card-subtitle">
                  This comparison resolves the exact misconception students struggle with in Machine Learning and Computer Science.
                </p>

                <div className="comparison-table-wrapper">
                  <table className="comparison-table">
                    <thead>
                      <tr>
                        <th style={{ width: '22%' }}>Dimension</th>
                        <th style={{ width: '39%' }} className="highlight-col-a">{activeGuide.comparison.termA}</th>
                        <th style={{ width: '39%' }} className="highlight-col-b">{activeGuide.comparison.termB}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td><strong>Meaning & Objective</strong></td>
                        <td>{activeGuide.comparison.meaningA}</td>
                        <td>{activeGuide.comparison.meaningB}</td>
                      </tr>
                      <tr>
                        <td><strong>Real-World Example</strong></td>
                        <td><em>{activeGuide.comparison.exampleA}</em></td>
                        <td><em>{activeGuide.comparison.exampleB}</em></td>
                      </tr>
                      <tr>
                        <td><strong>When to Prioritize</strong></td>
                        <td><span className="badge badge-success">{activeGuide.comparison.whenToUseA}</span></td>
                        <td><span className="badge badge-accent">{activeGuide.comparison.whenToUseB}</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* MISTIQ Pattern Trap & Memory Hook */}
              <div className="concept-dual-insights">
                <Card className="insight-card trap-card">
                  <div className="insight-badge trap-badge">
                    <Icon name="alert" />
                    <span>Why Students Confuse This</span>
                  </div>
                  <h4>The Common Trap</h4>
                  <p>{activeGuide.commonPitfall}</p>
                  <div className="insight-deep-dive">
                    <strong>MISTIQ-AMPA Insight:</strong>
                    <span>{activeGuide.keyInsight}</span>
                  </div>
                </Card>

                <Card className="insight-card memory-card">
                  <div className="insight-badge memory-badge">
                    <Icon name="lightbulb" />
                    <span>Memory Hook & Rule of Thumb</span>
                  </div>
                  <h4>How to Remember</h4>
                  <p className="memory-hook-text">{activeGuide.memoryHook}</p>
                  <div className="ready-quiz-box">
                    <span>Understood the concept?</span>
                    <Button onClick={() => startQuizForConcept(activeGuide.id)}>
                      Test this in Quiz Mode <span aria-hidden="true">→</span>
                    </Button>
                  </div>
                </Card>
              </div>
            </div>

            {/* Sidebar Guide Summary */}
            <aside className="concept-aside">
              <Card className="concept-aside-card">
                <span className="aside-mark" aria-hidden="true">📖</span>
                <h3>Concept Guide</h3>
                <p>Studying the theoretical distinction before taking questions prevents cognitive mistake reinforcement.</p>
                <div className="aside-rule" />
                <span className="aside-label">CURRENT CONCEPT</span>
                <strong>{activeGuide.title}</strong>
                <div style={{ marginTop: '14px' }}>
                  <span className="aside-label">AVAILABLE PRACTICE</span>
                  <strong>
                    {allQuestions.filter(q => q.topic.toLowerCase() === activeGuide.id.toLowerCase()).length || 2} questions in bank
                  </strong>
                </div>
                <div style={{ marginTop: '18px' }}>
                  <Button className="button-secondary full-width" onClick={() => startQuizForConcept(activeGuide.id)}>
                    Jump to Practice Quiz
                  </Button>
                </div>
              </Card>
            </aside>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 2: INTERACTIVE PRACTICE & QUIZ */}
      {/* ========================================================================= */}
      {activeTab === 'quiz' && (
        <>
          {loading && <LoadingState label="Finding question…" />}

          {error && !question && <ErrorState message={error} />}

          {!loading && !questions.length && (
            <Card>
              <EmptyState
                title="No questions are available yet"
                description="Once questions are added to the learning library, they will appear here."
              />
            </Card>
          )}

          {/* QUIZ COMPLETED / MARKS SUMMARY SCREEN */}
          {!loading && sessionFinished && sessionHistory.length > 0 && (
            <div className="quiz-results-view">
              <PageHeader
                title="Quiz Complete · Marks Summary"
                description="Your attempt sequence has been processed by MISTIQ-AMPA. Here is your performance breakdown."
              />

              <div className="results-grid">
                <Card className="marks-banner-card">
                  <div className="marks-header">
                    <span className="badge badge-success">Quiz Finished!</span>
                    <span className="marks-time">
                      Score: {sessionHistory.filter(r => r.correct).length} / {sessionHistory.length}
                    </span>
                  </div>

                  <div className="marks-body">
                    <div className="marks-big-number">
                      {Math.round((sessionHistory.filter(r => r.correct).length / sessionHistory.length) * 100)}%
                    </div>
                    <div className="marks-details">
                      <h3>
                        {sessionHistory.filter(r => r.correct).length} of {sessionHistory.length} answered correctly
                      </h3>
                      <p>
                        {sessionHistory.some(r => !r.correct)
                          ? 'You can review the conceptual distinctions below or revisit the Concept Guide.'
                          : 'Outstanding! Full accuracy on this practice session.'}
                      </p>
                    </div>
                  </div>

                  <div className="marks-actions" style={{ display: 'flex', gap: '12px', marginTop: '18px' }}>
                    <Button onClick={() => setActiveTab('learn')}>
                      📖 Review Concept Lessons
                    </Button>
                    <Button className="button-secondary" onClick={() => {
                      setIndex(0)
                      setSelected(null)
                      setResult(null)
                      setSessionHistory([])
                      setSessionFinished(false)
                    }}>
                      🔄 Retake Practice
                    </Button>
                  </div>
                </Card>

                {/* Question Review List */}
                <Card className="review-breakdown-card">
                  <h3>Question-by-Question Review</h3>
                  <div className="review-list">
                    {sessionHistory.map((rec, i) => (
                      <div key={i} className={`review-item ${rec.correct ? 'review-correct' : 'review-incorrect'}`}>
                        <div className="review-item-header">
                          <span className="review-q-num">Q{i + 1}</span>
                          <span className={`badge ${rec.correct ? 'badge-success' : 'badge-danger'}`}>
                            {rec.correct ? 'Correct' : 'Needs Review'}
                          </span>
                          <span className="review-time">{rec.responseTime}s</span>
                        </div>
                        <p className="review-question-text">{rec.question.question_text}</p>
                        <div className="review-answer-row">
                          <span>Your answer: <strong>Option {rec.selectedOption}: {optionText(rec.question, rec.selectedOption)}</strong></span>
                          {!rec.correct && (
                            <span className="review-expected">
                              Correct: <strong>Option {rec.correctOption}: {rec.correctAnswer}</strong>
                            </span>
                          )}
                        </div>
                        {!rec.correct && rec.mistakeType && (
                          <div className="review-remediation">
                            <span className="remediation-tag">MISTIQ Pattern: {mistakeLabels[rec.mistakeType as keyof typeof mistakeLabels] || rec.mistakeType}</span>
                            <button
                              type="button"
                              className="text-link-button"
                              onClick={() => {
                                setSelectedConceptId(rec.question.topic)
                                setActiveTab('learn')
                              }}
                            >
                              Study {rec.question.topic} concept lesson →
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* ACTIVE QUESTION SCREEN */}
          {!loading && !sessionFinished && question && (
            <>
              {/* Session Progress Header */}
              <div className="quiz-session-header">
                <div className="session-tracker">
                  <div className="session-progress-info">
                    <span className="session-q-counter">
                      Question <strong>{index + 1}</strong> of <strong>{questions.length}</strong>
                    </span>
                    {sessionHistory.length > 0 && (
                      <span className="session-live-score">
                        Current score: <strong>{sessionHistory.filter(r => r.correct).length} / {sessionHistory.length}</strong> correct
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
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button
                        type="button"
                        className="hint-toggle-btn"
                        onClick={() => setShowInQuizHint(prev => !prev)}
                        title="Toggle Concept Primer"
                      >
                        <Icon name="lightbulb" />
                        <span>{showInQuizHint ? 'Hide Concept Primer' : '💡 Concept Primer'}</span>
                      </button>
                      <span className="badge badge-accent difficulty-tag">Difficulty {question.difficulty}</span>
                    </div>
                  </div>

                  {/* Expandable In-Quiz Concept Primer Drawer */}
                  {showInQuizHint && (
                    <div className="in-quiz-concept-drawer">
                      <div className="drawer-header">
                        <strong>💡 Concept Primer: {getConceptGuide(question.topic).title}</strong>
                        <button type="button" className="drawer-close" onClick={() => setShowInQuizHint(false)}>✕</button>
                      </div>
                      <p className="drawer-summary">{getConceptGuide(question.topic).summary}</p>
                      <div className="drawer-rule">
                        <strong>Core Rule:</strong> {getConceptGuide(question.topic).formulaOrRule || getConceptGuide(question.topic).keyInsight}
                      </div>
                      <div className="drawer-footer">
                        <button
                          type="button"
                          className="text-link-button"
                          onClick={() => {
                            setSelectedConceptId(question.topic)
                            setActiveTab('learn')
                          }}
                        >
                          Open full concept lesson & comparison table →
                        </button>
                      </div>
                    </div>
                  )}

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
                          <h3>{result.attempt.correct ? 'Correct! Well done.' : 'Not quite.'}</h3>
                          <p>
                            The correct answer is <strong>{result.correct_option}. {result.correct_answer}</strong>
                          </p>

                          {result.mistake_event?.error_type === 'CONCEPT_CONFUSION' && (
                            <div className="aha-card">
                              <div className="card-kicker">A pattern MISTIQ noticed</div>
                              <strong>Concept Confusion Detected</strong>
                              <p className="confusion-pair">
                                {question.subtopic || question.topic} ↔ {optionText(question, result.attempt.selected_option)}
                              </p>
                              <p>Your choice links two closely related concepts that are commonly confused.</p>
                              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                                <Button
                                  onClick={() => {
                                    setSelectedConceptId(question.topic)
                                    setActiveTab('learn')
                                  }}
                                >
                                  📖 Learn {question.topic} Concept Guide
                                </Button>
                              </div>
                            </div>
                          )}

                          {result.mistake_event && result.mistake_event.error_type !== 'CONCEPT_CONFUSION' && (
                            <div className="aha-card">
                              <strong>{mistakeLabels[result.mistake_event.error_type]}</strong> in {result.mistake_event.topic}.
                              <p>Reviewing the underlying principles will help avoid this mistake pattern in future practice.</p>
                              <div style={{ marginTop: '8px' }}>
                                <button
                                  type="button"
                                  className="text-link-button"
                                  onClick={() => {
                                    setSelectedConceptId(question.topic)
                                    setActiveTab('learn')
                                  }}
                                >
                                  Read {question.topic} concept notes →
                                </button>
                              </div>
                            </div>
                          )}

                          {result.prediction && (
                            <p className="feedback-prediction">
                              MISTIQ-AMPA predicted next area to watch: {mistakeLabels[result.prediction.prediction]?.toLowerCase() || result.prediction.prediction}.
                            </p>
                          )}

                          <div style={{ display: 'flex', gap: '10px', marginTop: '16px', alignItems: 'center' }}>
                            <Button className="button-secondary" onClick={nextQuestion}>
                              {index + 1 >= questions.length ? 'Complete Quiz & View Marks' : 'Next question'} <span aria-hidden="true">→</span>
                            </Button>
                          </div>
                        </div>
                      </div>
                    )}
                  </Card>
                </div>

                <aside className="practice-aside">
                  <Card>
                    <span className="aside-mark" aria-hidden="true">🎯</span>
                    <h3>Active Quiz</h3>
                    <p>Give each question a thoughtful try. MISTIQ models your chronological error trajectory.</p>
                    <div className="aside-rule" />
                    <span className="aside-label">IN THIS QUIZ</span>
                    <strong>{questions.length} questions</strong>
                    <div style={{ marginTop: '12px' }}>
                      <span className="aside-label">NEED THEORY?</span>
                      <button
                        type="button"
                        className="text-link-button"
                        style={{ marginTop: '4px', display: 'block' }}
                        onClick={() => {
                          setSelectedConceptId(question.topic)
                          setActiveTab('learn')
                        }}
                      >
                        📖 Switch to Concept Lesson
                      </button>
                    </div>
                  </Card>
                </aside>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
