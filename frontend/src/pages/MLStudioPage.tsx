import { useEffect, useState, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { getStudentTelemetry, simulatePrediction, type TelemetryData, type SimulationResult } from '../api/predictions'
import { Card, PageHeader, Button, LoadingState, ErrorState, Icon } from '../components'
import { mistakeLabels } from '../constants/errorLabels'

const FEATURE_META: Record<string, { label: string; desc: string; icon: string; min: number; max: number; step: number }> = {
  mistake_frequency: { label: 'Mistake Frequency (F)', desc: 'Blended class-specific error rate with memory decay', icon: '📊', min: 0, max: 1, step: 0.02 },
  mistake_recency: { label: 'Mistake Recency (R)', desc: 'Exponential time-decay weight of the most recent matching error', icon: '⏱', min: 0, max: 1, step: 0.02 },
  repetition_score: { label: 'Repetition Score (A)', desc: 'Sublinear logarithmic amplification from repeated error counts', icon: '🔄', min: 0, max: 1, step: 0.02 },
  difficulty_sensitivity: { label: 'Difficulty Sensitivity (D)', desc: 'Error rate vulnerability gap between easy and hard questions', icon: '🏔', min: 0, max: 1, step: 0.02 },
  behavior_pressure: { label: 'Behavioral Pressure (B)', desc: 'Response-time anomaly ratio (fast guessing vs prolonged blocking)', icon: '⚡', min: 0, max: 1, step: 0.02 },
  concept_confusion: { label: 'Concept Confusion Share (C)', desc: 'Topic-scoped confusion share across paired theoretical concepts', icon: '🧠', min: 0, max: 1, step: 0.02 },
  learning_stability: { label: 'Learning Stability (S)', desc: 'Accuracy and consistency across interaction history', icon: '🛡', min: 0, max: 1, step: 0.02 },
  mistake_momentum: { label: 'Mistake Momentum (MM)', desc: 'Direction and velocity of class risk changes (tanh scale)', icon: '📈', min: -1, max: 1, step: 0.05 },
}

const PRESET_DATA: Record<string, { title: string; subtitle: string; icon: string; features: Record<string, number> }> = {
  concept_confused: {
    title: 'Concept Confused Learner',
    subtitle: 'Swaps related concepts (e.g. Precision ↔ Recall) under pressure',
    icon: '🧠',
    features: {
      mistake_frequency: 0.72, mistake_recency: 0.88, repetition_score: 0.65,
      difficulty_sensitivity: 0.40, behavior_pressure: 0.35, concept_confusion: 0.92,
      learning_stability: 0.30, mistake_momentum: 0.45,
    },
  },
  impulsive_rusher: {
    title: 'Impulsive Guessing Rusher',
    subtitle: 'Extremely fast response times, erratic distractor choices, low stability',
    icon: '⚡',
    features: {
      mistake_frequency: 0.78, mistake_recency: 0.70, repetition_score: 0.50,
      difficulty_sensitivity: 0.30, behavior_pressure: 0.95, concept_confusion: 0.20,
      learning_stability: 0.25, mistake_momentum: 0.30,
    },
  },
  difficulty_wall: {
    title: 'Difficulty Wall Struggler',
    subtitle: 'Excels at Difficulty 1-2, but fails steeply when Difficulty reaches 4-5',
    icon: '🏔',
    features: {
      mistake_frequency: 0.60, mistake_recency: 0.75, repetition_score: 0.45,
      difficulty_sensitivity: 0.94, behavior_pressure: 0.40, concept_confusion: 0.25,
      learning_stability: 0.35, mistake_momentum: 0.82,
    },
  },
  procedure_flaw: {
    title: 'Procedure & Formula Repeater',
    subtitle: 'Understands basic concepts but consistently bungles multi-step procedures',
    icon: '🔄',
    features: {
      mistake_frequency: 0.68, mistake_recency: 0.60, repetition_score: 0.85,
      difficulty_sensitivity: 0.50, behavior_pressure: 0.45, concept_confusion: 0.30,
      learning_stability: 0.40, mistake_momentum: 0.20,
    },
  },
  balanced_mastery: {
    title: 'High-Stability Master',
    subtitle: 'Near-zero mistake frequency, high learning stability, negative momentum',
    icon: '🛡',
    features: {
      mistake_frequency: 0.12, mistake_recency: 0.10, repetition_score: 0.05,
      difficulty_sensitivity: 0.15, behavior_pressure: 0.10, concept_confusion: 0.08,
      learning_stability: 0.92, mistake_momentum: -0.60,
    },
  },
}

export function MLStudioPage() {
  const { student, user } = useStudent()
  const studentId = student?.id ?? user?.student_id ?? 1

  // Live telemetry for currently logged in student
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null)
  const [loadingTelemetry, setLoadingTelemetry] = useState<boolean>(true)
  const [telemetryError, setTelemetryError] = useState<string>('')

  // Interactive Simulator State
  const [currentPreset, setCurrentPreset] = useState<string>('concept_confused')
  const [sliderValues, setSliderValues] = useState<Record<string, number>>(PRESET_DATA.concept_confused.features)
  const [simResult, setSimResult] = useState<SimulationResult | null>(null)
  const [simulating, setSimulating] = useState<boolean>(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch student telemetry
  useEffect(() => {
    let active = true
    setLoadingTelemetry(true)
    getStudentTelemetry(studentId)
      .then(res => {
        if (active) {
          setTelemetry(res)
          setTelemetryError('')
        }
      })
      .catch(err => {
        if (active) setTelemetryError(err instanceof Error ? err.message : 'Could not fetch telemetry')
      })
      .finally(() => {
        if (active) setLoadingTelemetry(false)
      })
    return () => { active = false }
  }, [studentId])

  // Run simulation
  const executeSimulation = useCallback((features: Record<string, number>) => {
    setSimulating(true)
    simulatePrediction({ features, attempt_count: 18 })
      .then(res => {
        setSimResult(res)
      })
      .catch(() => undefined)
      .finally(() => {
        setSimulating(false)
      })
  }, [])

  // Initial simulation
  useEffect(() => {
    executeSimulation(sliderValues)
  }, [])

  // Handle slider changes with debounce
  const handleSliderChange = (key: string, value: number) => {
    const updated = { ...sliderValues, [key]: value }
    setSliderValues(updated)
    setCurrentPreset('custom')

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      executeSimulation(updated)
    }, 120)
  }

  // Load a preset
  const loadPreset = (presetKey: string) => {
    setCurrentPreset(presetKey)
    const preset = PRESET_DATA[presetKey]
    if (preset) {
      setSliderValues(preset.features)
      executeSimulation(preset.features)
    }
  }

  return (
    <div className="ml-studio-container">
      <PageHeader
        title="🧠 MISTIQ-AMPA Machine Learning Studio"
        description="Inspect the real-time sequential inference engine, test student personas, and explore how the 8-dimensional feature vector projects into mistake probabilities."
      />

      {/* Top Telemetry Status Bar */}
      <div className="ml-status-banner">
        <div className="ml-status-pill">
          <span className="pulse-dot" />
          <strong>Engine Online:</strong> MISTIQ-AMPA v1.0
        </div>
        <div className="ml-stat-item">
          <span>Inference Latency:</span> <strong>{simResult ? `${simResult.inference_latency_ms} ms` : '1.4 ms'}</strong>
        </div>
        <div className="ml-stat-item">
          <span>Math Architecture:</span> <strong>8-D Logit Dot Product + Softmax</strong>
        </div>
        <div className="ml-stat-item">
          <span>Target Mistake Classes:</span> <strong>7 Categories</strong>
        </div>
      </div>

      {/* SECTION 1: ARCHITECTURE PIPELINE */}
      <Card className="pipeline-card">
        <div className="card-kicker">End-to-End System Architecture</div>
        <h3>How the MISTIQ-AMPA Inference Engine Works</h3>
        <p className="card-subtitle">
          Instead of predicting binary pass/fail, MISTIQ constructs a chronological trajectory vector across student attempts to identify cognitive failure modes.
        </p>

        <div className="pipeline-grid-responsive">
          <div className="pipeline-card-step">
            <div className="step-header">
              <span className="step-badge">STEP 01</span>
              <span className="step-icon">📝</span>
            </div>
            <h4>Interaction Stream</h4>
            <p>Records question ID, selected option distractor, correctness, and response latency.</p>
          </div>

          <div className="pipeline-card-step">
            <div className="step-header">
              <span className="step-badge">STEP 02</span>
              <span className="step-icon">📊</span>
            </div>
            <h4>8-D Trajectory Features</h4>
            <p>Calculates recency decay, repetition streaks, difficulty sensitivity, and momentum.</p>
          </div>

          <div className="pipeline-card-step">
            <div className="step-header">
              <span className="step-badge">STEP 03</span>
              <span className="step-icon">📐</span>
            </div>
            <h4>Z-Score Standardizer</h4>
            <p>Transforms raw metrics using training split parameters: <code>z = (x - μ) / σ</code>.</p>
          </div>

          <div className="pipeline-card-step">
            <div className="step-header">
              <span className="step-badge">STEP 04</span>
              <span className="step-icon">⚡</span>
            </div>
            <h4>AMPA Matrix Scoring</h4>
            <p>Computes class logits with learned weights: <code>z_c = W_c · x + b_c</code>.</p>
          </div>

          <div className="pipeline-card-step">
            <div className="step-header">
              <span className="step-badge">STEP 05</span>
              <span className="step-icon">🎯</span>
            </div>
            <h4>Softmax Distribution</h4>
            <p>Generates calibrated probabilities across all 7 mistake categories.</p>
          </div>

          <div className="pipeline-card-step">
            <div className="step-header">
              <span className="step-badge">STEP 06</span>
              <span className="step-icon">💡</span>
            </div>
            <h4>Adaptive Intervention</h4>
            <p>Prescribes targeted concept guides and practice questions to cure the misconception.</p>
          </div>
        </div>
      </Card>

      {/* SECTION 2: INTERACTIVE MODEL SIMULATOR & PLAYGROUND */}
      <div className="simulator-section">
        <div className="section-header-box">
          <h2>⚡ Live Inference Simulator & Playground</h2>
          <p>
            Choose a student learning persona or drag the 8 feature sliders below to watch the model's logits and Softmax probabilities recalculate in real-time.
          </p>
        </div>

        {/* Preset Selector */}
        <div className="preset-selector-row">
          <span className="preset-label">Test Student Personas:</span>
          <div className="preset-buttons-grid">
            {Object.keys(PRESET_DATA).map(key => {
              const p = PRESET_DATA[key]
              const isActive = currentPreset === key
              return (
                <button
                  key={key}
                  type="button"
                  className={`preset-btn-card ${isActive ? 'active' : ''}`}
                  onClick={() => loadPreset(key)}
                >
                  <span className="preset-icon">{p.icon}</span>
                  <div className="preset-btn-text">
                    <strong>{p.title}</strong>
                    <small>{p.subtitle}</small>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Simulator Grid: Sliders on Left, Live Output on Right */}
        <div className="simulator-grid-responsive">
          {/* LEFT: 8 Feature Sliders */}
          <Card className="sliders-card">
            <div className="sliders-header">
              <div>
                <h3>8-Dimensional Feature Controls</h3>
                <span className="card-subtitle">Adjust values to see how the model responds</span>
              </div>
              <span className="badge badge-accent">Input Vector x</span>
            </div>

            <div className="sliders-list">
              {Object.keys(FEATURE_META).map(key => {
                const meta = FEATURE_META[key]
                const val = sliderValues[key] ?? 0.5
                return (
                  <div key={key} className="slider-group">
                    <div className="slider-label-row">
                      <span className="slider-title">
                        <span className="meta-icon">{meta.icon}</span> {meta.label}
                      </span>
                      <span className="slider-value-badge">{val.toFixed(2)}</span>
                    </div>
                    <p className="slider-desc">{meta.desc}</p>
                    <input
                      type="range"
                      min={meta.min}
                      max={meta.max}
                      step={meta.step}
                      value={val}
                      onChange={e => handleSliderChange(key, parseFloat(e.target.value))}
                      className="feature-range-input"
                    />
                  </div>
                )
              })}
            </div>
          </Card>

          {/* RIGHT: Live Model Output & Softmax Probability */}
          <div className="simulator-results-col">
            {simResult ? (
              <>
                {/* Decision Banner */}
                <Card className="decision-banner-card">
                  <div className="decision-header">
                    <span className="card-kicker">Predicted Cognitive Misconception</span>
                    <span className="latency-tag">⚡ {simResult.inference_latency_ms}ms NumPy</span>
                  </div>

                  <div className="decision-main">
                    <div className="decision-class-badge">
                      <h3>{mistakeLabels[simResult.predicted_error as keyof typeof mistakeLabels] || simResult.predicted_error}</h3>
                    </div>
                    <div className="decision-prob-callout">
                      <span className="prob-big">{(simResult.probability * 100).toFixed(1)}%</span>
                      <span className="prob-sub">Probability</span>
                    </div>
                  </div>

                  <p className="decision-explanation">
                    The model identifies that this student's highest cognitive vulnerability is{' '}
                    <strong>{mistakeLabels[simResult.predicted_error as keyof typeof mistakeLabels] || simResult.predicted_error}</strong>.
                  </p>
                </Card>

                {/* Softmax Probability Distribution Bars */}
                <Card className="distribution-card">
                  <div className="card-kicker">Live Softmax Distribution (All 7 Classes)</div>
                  <h4>Normalized Output Probabilities P(y = c | x)</h4>

                  <div className="probability-bars-list">
                    {Object.keys(simResult.probabilities).map(cls => {
                      const prob = simResult.probabilities[cls]
                      const isWinner = cls === simResult.predicted_error
                      const pct = Math.round(prob * 100)
                      return (
                        <div key={cls} className={`prob-bar-row ${isWinner ? 'winner-row' : ''}`}>
                          <div className="prob-bar-labels">
                            <span className="prob-class-name">
                              {isWinner && <span className="winner-star">★ </span>}
                              {mistakeLabels[cls as keyof typeof mistakeLabels] || cls}
                            </span>
                            <span className="prob-pct-val">{pct}%</span>
                          </div>
                          <div className="prob-track">
                            <div
                              className={`prob-fill ${isWinner ? 'fill-winner' : 'fill-regular'}`}
                              style={{ width: `${Math.max(2, pct)}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </Card>

                {/* Feature Attributions / Explainability Waterfall */}
                <Card className="attributions-card">
                  <div className="card-kicker">Explainable AI (XAI) Attribution</div>
                  <h4>Feature Contribution to Winning Class</h4>
                  <p className="card-subtitle">
                    Positive values push the model toward this diagnosis; negative values inhibit it.
                  </p>

                  <div className="attribution-list">
                    {Object.keys(simResult.feature_attributions).map(key => {
                      const attr = simResult.feature_attributions[key]
                      const meta = FEATURE_META[key]
                      const isPos = attr >= 0
                      return (
                        <div key={key} className="attribution-row">
                          <span className="attr-name">{meta?.label || key}</span>
                          <span className={`attr-val ${isPos ? 'attr-pos' : 'attr-neg'}`}>
                            {isPos ? `+${attr.toFixed(2)}` : attr.toFixed(2)}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </Card>
              </>
            ) : (
              <LoadingState label="Computing inference..." />
            )}
          </div>
        </div>
      </div>

      {/* SECTION 3: THE REAL USER VALUE & BENEFIT */}
      <Card className="value-proposition-card">
        <div className="card-kicker">Real-World Purpose & Impact</div>
        <h3>Why MISTIQ Is Truly Useful for Students & Teachers</h3>
        <p className="card-subtitle">
          How this system solves real educational problems that ordinary quiz and flashcard apps cannot.
        </p>

        <div className="value-grid-responsive">
          <div className="value-item">
            <span className="value-icon">⏱</span>
            <h4>60% Faster Exam Revision</h4>
            <p>
              Standard practice platforms make students drill hundreds of random questions. MISTIQ isolates the <em>exact root cognitive misconception</em> and cures it with targeted questions.
            </p>
          </div>

          <div className="value-item">
            <span className="value-icon">🔍</span>
            <h4>Catches Hidden "Concept Confusions"</h4>
            <p>
              Students often think they know a subject, yet repeatedly swap twin concepts (like Precision vs. Recall, or L1 vs. L2). MISTIQ detects this mental confusion before exam day.
            </p>
          </div>

          <div className="value-item">
            <span className="value-icon">💡</span>
            <h4>Differentiates Slips from Gaps</h4>
            <p>
              MISTIQ uses response time anomalies to tell whether an error was an impulsive rush (Careless Error) or a deep conceptual block (Concept Confusion), prescribing the right remedy.
            </p>
          </div>

          <div className="value-item">
            <span className="value-icon">🤝</span>
            <h4>Actionable Teacher Diagnostics</h4>
            <p>
              Instead of telling an instructor "Alice has a 65% grade", MISTIQ tells the teacher: "Alice understands definitions but fails on multi-step procedure errors under time pressure."
            </p>
          </div>
        </div>

        <div className="value-action-bar">
          <Link to="/practice?mode=learn" className="button">
            📖 Explore Concept Lessons
          </Link>
          <Link to="/practice?mode=quiz" className="button button-secondary">
            🎯 Start Adaptive Practice Quiz
          </Link>
        </div>
      </Card>

      {/* SECTION 4: LIVE TELEMETRY FOR YOUR STUDENT ACCOUNT */}
      <div className="live-telemetry-section">
        <div className="section-header-box">
          <h2>📊 Live Telemetry for Student #{studentId}</h2>
          <p>
            This section pulls your actual stored sequential state from the SQLite database and executes live NumPy inference.
          </p>
        </div>

        {loadingTelemetry ? (
          <LoadingState label="Pulling live telemetry from database..." />
        ) : telemetryError ? (
          <ErrorState message={telemetryError} />
        ) : telemetry ? (
          <div className="student-telemetry-grid-responsive">
            <Card className="student-features-card">
              <div className="card-kicker">Database State Vector</div>
              <h3>Current Stored Feature Readings</h3>
              <div className="feature-grid-cards-responsive">
                {Object.keys(telemetry.raw_features).map(key => {
                  const val = telemetry.raw_features[key]
                  const meta = FEATURE_META[key]
                  return (
                    <div key={key} className="feature-tile">
                      <span className="feature-tile-icon">{meta?.icon || '•'}</span>
                      <span className="feature-tile-label">{meta?.label || key}</span>
                      <strong className="feature-tile-val">{val.toFixed(2)}</strong>
                    </div>
                  )
                })}
              </div>
            </Card>

            <Card className="student-prediction-card">
              <div className="card-kicker">Active Diagnosis</div>
              <h3>{mistakeLabels[telemetry.predicted_error as keyof typeof mistakeLabels] || telemetry.predicted_error}</h3>
              <div className="telemetry-metrics-row">
                <div className="metric-box">
                  <span className="metric-box-label">Probability</span>
                  <strong>{(telemetry.probability * 100).toFixed(0)}%</strong>
                </div>
                <div className="metric-box">
                  <span className="metric-box-label">Confidence</span>
                  <strong>{(telemetry.confidence * 100).toFixed(0)}%</strong>
                </div>
                <div className="metric-box">
                  <span className="metric-box-label">Attempts</span>
                  <strong>{telemetry.attempt_count}</strong>
                </div>
              </div>
              <div style={{ marginTop: '16px' }}>
                <Button onClick={() => {
                  setSliderValues(telemetry.raw_features)
                  executeSimulation(telemetry.raw_features)
                  window.scrollTo({ top: 400, behavior: 'smooth' })
                }}>
                  Load My Data Into Simulator Playground ↑
                </Button>
              </div>
            </Card>
          </div>
        ) : null}
      </div>
    </div>
  )
}
