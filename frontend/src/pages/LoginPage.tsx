import { useState, type FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useStudent, getRecentStudents } from '../context/StudentContext'
import { Button, Card, ErrorState } from '../components'
import { ApiError } from '../api/client'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { enter, reconnect, login, restoreError, clearRestoreError } = useStudent()

  // Username & Password credentials
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  // Local profile creation
  const [name, setName] = useState('')
  const [studentId, setStudentId] = useState('')
  const [selectedTrack, setSelectedTrack] = useState('Machine Learning & Evaluation')

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const recentStudents = getRecentStudents()
  const from = (location.state as any)?.from || '/dashboard'

  // Standard Username & Password sign-in
  const handlePasswordLogin = async (e: FormEvent) => {
    e.preventDefault()
    if (!loginUsername.trim() || !loginPassword) return
    setBusy(true)
    setError('')
    try {
      await login(loginUsername.trim(), loginPassword)
      const destination = loginUsername.trim().toLowerCase() === 'admin' ? '/research' : from
      navigate(destination, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError('MISTIQ could not reach the learning service. Check that the backend is running.')
      } else {
        setError(err instanceof Error ? err.message : 'Incorrect username or password. Please try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  // Quick 1-click credential autofill
  const fillCredentials = (user: string, pass: string) => {
    setLoginUsername(user)
    setLoginPassword(pass)
    clearRestoreError()
    setError('')
  }

  // Local profile creation (Name only)
  const handleCreateProfile = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    setError('')
    try {
      await enter(name.trim())
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError('MISTIQ could not reach the learning service. Check that the backend is running.')
      } else {
        setError(err instanceof Error ? err.message : 'Could not create profile. Please try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  // Reconnect with Student ID
  const handleReconnectProfile = async (e?: FormEvent, targetId?: number) => {
    if (e) e.preventDefault()
    const idToUse = targetId !== undefined ? targetId : parseInt(studentId, 10)
    if (isNaN(idToUse) || idToUse <= 0) return
    setBusy(true)
    setError('')
    try {
      await reconnect(idToUse)
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError('MISTIQ could not reach the learning service. Check that the backend is running.')
      } else {
        setError(err instanceof Error ? err.message : 'Student profile not found. Please check your ID.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="entry-page">
      {/* Educational Platform Portal Header */}
      <header className="entry-topbar">
        <div className="portal-brand">
          <div className="brand-mark" aria-hidden="true">M</div>
          <div className="brand-copy">
            <span className="brand-name">MISTIQ</span>
            <span className="brand-tag">Adaptive Mistake Intelligence Platform</span>
          </div>
        </div>
        <div className="portal-status-badge">
          <span className="status-dot-pulse" aria-hidden="true" />
          <span>Local Engine &amp; SQLite Ready</span>
        </div>
      </header>

      <div className="entry-grid">
        {/* Left Hero Section: Educational Value Proposition */}
        <section className="entry-intro">
          <span className="eyebrow">Adaptive Learning Intelligence</span>
          <h1>A learning system that predicts what a student may struggle with next by learning from how their mistakes evolve over time.</h1>
          <p>
            MISTIQ turns incorrect answers into structured learning opportunities. By classifying mistake types (concept confusions, calculation errors, traps) and tracking sequential transitions with AMPA Markov models, MISTIQ guides your practice directly to the root of your misconceptions.
          </p>

          <div className="portal-features-grid">
            <div className="portal-feature-item">
              <div className="feature-icon" aria-hidden="true">🎯</div>
              <div>
                <strong>Targeted Mistake Remediation</strong>
                <p>Pinpoint exact conceptual traps like Precision vs Recall with focused drills.</p>
              </div>
            </div>
            <div className="portal-feature-item">
              <div className="feature-icon" aria-hidden="true">🧠</div>
              <div>
                <strong>AMPA Markov Transitions</strong>
                <p>Calculates empirical transition matrices to predict likely upcoming confusion states.</p>
              </div>
            </div>
            <div className="portal-feature-item">
              <div className="feature-icon" aria-hidden="true">🛡️</div>
              <div>
                <strong>100% Local &amp; Empirical</strong>
                <p>Every accuracy metric, recovery signal, and prediction is computed from your practice in the local database.</p>
              </div>
            </div>
          </div>

          <div className="entry-note">
            <span className="note-mark" aria-hidden="true">✳</span>
            <span>Every number you see — accuracy, predictions, recommendations — is computed from your own recorded practice in MISTIQ's local database. No sample data.</span>
          </div>

          <div className="showcase-cta">
            <a className="button" href="#create-profile">
              Create your local profile <span aria-hidden="true">→</span>
            </a>
            <a className="text-link" href="#learn-more">
              How it works
            </a>
          </div>
        </section>

        {/* Right Auth Portal Column */}
        <div className="auth-portal-column">
          {/* Main Card: Proper Username and Password Sign-in */}
          <Card className="entry-card" id="signin-card">
            <div className="portal-tab-header">
              <span className="eyebrow">Sign In with Credentials</span>
            </div>

            <h2>Sign in to MISTIQ</h2>
            <p>Enter your username and password to resume your learning session.</p>

            {restoreError && (
              <div style={{ marginTop: '12px' }}>
                <ErrorState message={restoreError} />
              </div>
            )}
            {error && (
              <div style={{ marginTop: '12px' }}>
                <ErrorState message={error} />
              </div>
            )}

            <form onSubmit={handlePasswordLogin} className="form-stack">
              <label htmlFor="login-username">Username</label>
              <input
                id="login-username"
                value={loginUsername}
                onChange={e => {
                  setLoginUsername(e.target.value)
                  if (restoreError) clearRestoreError()
                  if (error) setError('')
                }}
                placeholder="e.g. student or admin"
                required
              />

              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                value={loginPassword}
                onChange={e => {
                  setLoginPassword(e.target.value)
                  if (restoreError) clearRestoreError()
                  if (error) setError('')
                }}
                placeholder="Enter your password"
                required
              />

              <Button type="submit" disabled={busy || !loginUsername.trim() || !loginPassword}>
                {busy ? 'Signing in…' : 'Sign in with Password'} <span aria-hidden="true">→</span>
              </Button>
            </form>

            {/* Quick Demo Credentials Autofill */}
            <div className="demo-credentials-box">
              <span className="demo-cred-label">Quick Demo Credentials:</span>
              <div className="demo-cred-actions">
                <button
                  type="button"
                  className="button button-secondary"
                  style={{ fontSize: '11.5px', padding: '5px 10px' }}
                  onClick={() => fillCredentials('student', 'student123')}
                >
                  🎓 Demo Student (student)
                </button>
                <button
                  type="button"
                  className="button button-secondary"
                  style={{ fontSize: '11.5px', padding: '5px 10px' }}
                  onClick={() => fillCredentials('admin', 'admin')}
                >
                  🔬 Admin (admin)
                </button>
              </div>
            </div>
          </Card>

          {/* Secondary Card: Local Profile Creation & Student ID Reconnect */}
          <Card className="entry-card" id="create-profile" style={{ marginTop: '20px' }}>
            <span className="eyebrow">Local Profile &amp; Enrollment</span>
            <h2>Continue with a local profile</h2>
            <p>Your profile, practice history, and predictions are stored in the local MISTIQ database on this machine. No account, email, or sign-up is required.</p>

            {/* Learning Track Selector */}
            <div className="track-selector">
              <span className="track-label">Target Learning Track:</span>
              <div className="track-pills">
                {['Machine Learning & Evaluation', 'Classification & Confusion Pairs', 'Statistical Diagnostics'].map(track => (
                  <button
                    key={track}
                    type="button"
                    className={`track-pill ${selectedTrack === track ? 'active' : ''}`}
                    onClick={() => setSelectedTrack(track)}
                  >
                    {track}
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleCreateProfile} className="form-stack">
              <label htmlFor="student-name">Your name</label>
              <input
                id="student-name"
                value={name}
                maxLength={200}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. Alex or Maya"
                required
              />
              <Button type="submit" disabled={busy || !name.trim()}>
                {busy ? 'Enrolling…' : 'Create my local profile'} <span aria-hidden="true">→</span>
              </Button>
            </form>

            {/* Quick Profile Resume for Returning Learners */}
            {recentStudents.length > 0 && (
              <div className="recent-profiles-box">
                <span className="recent-profiles-label">Recent Profiles On This Machine:</span>
                <div className="recent-profiles-list">
                  {recentStudents.map(r => (
                    <button
                      key={r.id}
                      type="button"
                      className="recent-profile-chip"
                      onClick={() => handleReconnectProfile(undefined, r.id)}
                      disabled={busy}
                    >
                      <span className="recent-chip-avatar">{r.name.slice(0, 1).toUpperCase()}</span>
                      <span className="recent-chip-name">{r.name}</span>
                      <span className="recent-chip-id">#{r.id}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="form-divider"><span>Already have a profile?</span></div>

            {/* 1-Click Demo Shortcut */}
            <div className="demo-quickstart-banner">
              <button
                type="button"
                className="demo-quickstart-btn"
                onClick={() => {
                  setStudentId('1')
                  handleReconnectProfile(undefined, 1)
                }}
                disabled={busy}
              >
                <span className="demo-sparkle" aria-hidden="true">⚡</span>
                <span><strong>1-Click Demo:</strong> Load Demo Account (ID: 1)</span>
              </button>
            </div>

            <form onSubmit={handleReconnectProfile} className="form-stack">
              <label htmlFor="student-id">Student ID</label>
              <div className="inline-form">
                <input
                  id="student-id"
                  type="number"
                  min="1"
                  value={studentId}
                  onChange={e => setStudentId(e.target.value)}
                  placeholder="Enter your ID (e.g. 1)"
                  required
                />
                <Button type="submit" className="button-secondary" disabled={busy || !studentId}>
                  Continue
                </Button>
              </div>
            </form>
          </Card>
        </div>
      </div>

      {/* How It Works Section */}
      <section className="learn-more" id="learn-more">
        <div className="learn-copy">
          <div className="card-kicker">How it works</div>
          <h2>A loop that learns from each attempt.</h2>
          <p>MISTIQ runs entirely on this machine. Every number you see is computed from your own recorded practice in the local database.</p>
        </div>
        <div className="learn-steps">
          <article>
            <span className="learn-step-num">1</span>
            <h3>Create a local profile</h3>
            <p>No account, email, or sign-up. Reconnect anytime with your student ID.</p>
          </article>
          <article>
            <span className="learn-step-num">2</span>
            <h3>Practice and get checked</h3>
            <p>Answer questions with immediate, honest feedback. Attempts and mistakes are recorded as they happen.</p>
          </article>
          <article>
            <span className="learn-step-num">3</span>
            <h3>See what may come next</h3>
            <p>AMPA predicts a likely next challenge and suggests a question, using only your real history.</p>
          </article>
        </div>
      </section>

      <footer className="entry-footer">MISTIQ 2.0 &middot; Local learning profiles</footer>
    </main>
  )
}
