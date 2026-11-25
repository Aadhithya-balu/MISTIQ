import { useState, type FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useStudent } from '../context/StudentContext'
import { Button, Card, ErrorState } from '../components'
import { ApiError } from '../api/client'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { enter, reconnect, login, register, restoreError, clearRestoreError } = useStudent()

  // Tab: 'signin' | 'register'
  const [tab, setTab] = useState<'signin' | 'register'>('register')

  // Sign In state
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  // Register / Local Profile state
  const [registerName, setRegisterName] = useState('')
  const [registerUsername, setRegisterUsername] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')

  // Legacy Student ID reconnect
  const [studentId, setStudentId] = useState('')

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const from = (location.state as any)?.from || '/dashboard'

  const handleSignIn = async (e: FormEvent) => {
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
        setError('Could not reach the learning service. Check that the backend is running.')
      } else {
        setError(err instanceof Error ? err.message : 'Incorrect username or password. Please try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  const handleCreateAccount = async (e: FormEvent) => {
    e.preventDefault()
    if (!registerName.trim()) return
    setBusy(true)
    setError('')
    try {
      if (registerUsername.trim() && registerPassword) {
        await register(registerName.trim(), registerUsername.trim(), registerPassword)
      } else {
        await enter(registerName.trim())
      }
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError('Could not reach the learning service. Check that the backend is running.')
      } else {
        setError(err instanceof Error ? err.message : 'Could not set up profile. Please try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  const handleReconnectProfile = async (e: FormEvent) => {
    e.preventDefault()
    const idToUse = parseInt(studentId, 10)
    if (isNaN(idToUse) || idToUse <= 0) return
    setBusy(true)
    setError('')
    try {
      await reconnect(idToUse)
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError('Could not reach the learning service. Check that the backend is running.')
      } else {
        setError(err instanceof Error ? err.message : 'Student profile not found. Please check your ID.')
      }
    } finally {
      setBusy(false)
    }
  }

  const handleQuickDemo = async (role: 'student' | 'admin') => {
    setBusy(true)
    setError('')
    clearRestoreError()
    try {
      if (role === 'admin') {
        await login('admin', 'admin')
        navigate('/research', { replace: true })
      } else {
        await login('student', 'student123')
        navigate('/dashboard', { replace: true })
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError('Could not reach the learning service. Check that the backend is running.')
      } else {
        setError(err instanceof Error ? err.message : 'Could not sign in with demo credentials.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="entry-page">
      <header className="entry-topbar">
        <div className="portal-brand">
          <div className="brand-mark" aria-hidden="true">M</div>
          <div className="brand-copy">
            <span className="brand-name">MISTIQ</span>
            <span className="brand-tag">Adaptive Learning &amp; Concept Mastery</span>
          </div>
        </div>
        <div className="portal-status-badge">
          <span className="status-dot-pulse" aria-hidden="true" />
          <span>Learning Platform Active</span>
        </div>
      </header>

      <div className="entry-grid">
        {/* Left Hero Section: LMS Value Proposition */}
        <section className="entry-intro">
          <span className="eyebrow">Personalized Concept Mastery</span>
          <h1>A learning system that predicts what a student may struggle with next by learning from how their mistakes evolve over time.</h1>
          <p>
            Unlike traditional platforms that just say "Incorrect" and move on, MISTIQ learns why you struggled—whether it was conceptual confusion, a missed step, or a tricky distractor—and recommends the exact lesson to fix it.
          </p>

          <div className="portal-features-grid">
            <div className="portal-feature-item">
              <div className="feature-icon" aria-hidden="true">🎯</div>
              <div>
                <strong>Targeted Conceptual Clarification</strong>
                <p>Pinpoint confusing dual concepts (like Precision vs. Recall or L1 vs. L2) before exam day.</p>
              </div>
            </div>
            <div className="portal-feature-item">
              <div className="feature-icon" aria-hidden="true">📈</div>
              <div>
                <strong>Adaptive Learning Path</strong>
                <p>Quizzes and recommendations adapt automatically based on your real practice history.</p>
              </div>
            </div>
            <div className="portal-feature-item">
              <div className="feature-icon" aria-hidden="true">💡</div>
              <div>
                <strong>Intuition-First Explanations</strong>
                <p>Clear, side-by-side mental models and distractor breakdowns for every problem.</p>
              </div>
            </div>
          </div>

          <div className="entry-note">
            <span className="note-mark" aria-hidden="true">✳</span>
            <span>Your progress, review items, and recommended lessons are computed from your own practice sessions.</span>
          </div>

          <div className="showcase-cta" style={{ marginTop: '20px' }}>
            <a className="text-link" href="#learn-more">
              How it works <span aria-hidden="true">→</span>
            </a>
          </div>
        </section>

        {/* Right Auth Portal Column: Single Clean LMS Authentication Card */}
        <div className="auth-portal-column">
          <Card className="entry-card" id="auth-card">
            <span className="eyebrow">Student &amp; Educator Portal</span>
            <p style={{ fontSize: '13px', color: 'var(--muted)', marginTop: '4px', marginBottom: '14px' }}>
              <span>Continue with a local profile</span> or sign in with your credentials.
            </p>

            {/* Mode Switcher Tabs */}
            <div className="auth-tab-bar" style={{ display: 'flex', gap: '8px', marginBottom: '18px', borderBottom: '1px solid var(--line)', paddingBottom: '10px' }}>
              <button
                type="button"
                className={`button ${tab === 'signin' ? '' : 'button-secondary'}`}
                style={{ flex: 1, padding: '9px 12px' }}
                onClick={() => { setTab('signin'); setError('') }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`button ${tab === 'register' ? '' : 'button-secondary'}`}
                style={{ flex: 1, padding: '9px 12px' }}
                onClick={() => { setTab('register'); setError('') }}
              >
                Create Account
              </button>
            </div>

            {tab === 'signin' ? (
              <>
                <h2>Welcome Back</h2>
                <p style={{ color: 'var(--muted)', fontSize: '13.5px', marginBottom: '16px' }}>
                  Sign in to continue your courses and practice sessions.
                </p>

                {restoreError && (
                  <div style={{ marginBottom: '12px' }}>
                    <ErrorState message={restoreError} />
                  </div>
                )}
                {error && (
                  <div style={{ marginBottom: '12px' }}>
                    <ErrorState message={error} />
                  </div>
                )}

                <form onSubmit={handleSignIn} className="form-stack">
                  <label htmlFor="login-username">Username</label>
                  <input
                    id="login-username"
                    value={loginUsername}
                    onChange={e => {
                      setLoginUsername(e.target.value)
                      if (restoreError) clearRestoreError()
                      if (error) setError('')
                    }}
                    placeholder="Enter your username (e.g. student)"
                    required
                    autoComplete="username"
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
                    autoComplete="current-password"
                  />

                  <Button type="submit" disabled={busy || !loginUsername.trim() || !loginPassword}>
                    {busy ? 'Signing in…' : 'Sign In'} <span aria-hidden="true">→</span>
                  </Button>
                </form>
              </>
            ) : (
              <>
                <h2>Create Your Student Profile</h2>
                <p style={{ color: 'var(--muted)', fontSize: '13.5px', marginBottom: '16px' }}>
                  Enroll in MISTIQ to receive adaptive practice and concept mastery guidance. No account, email, or sign-up is required.
                </p>

                {error && (
                  <div style={{ marginBottom: '12px' }}>
                    <ErrorState message={error} />
                  </div>
                )}

                <form onSubmit={handleCreateAccount} className="form-stack">
                  <label htmlFor="student-name">Your name</label>
                  <input
                    id="student-name"
                    value={registerName}
                    onChange={e => {
                      setRegisterName(e.target.value)
                      if (error) setError('')
                    }}
                    placeholder="e.g. Alex Johnson"
                    required
                    autoComplete="name"
                  />

                  <label htmlFor="register-username">Username (Optional)</label>
                  <input
                    id="register-username"
                    value={registerUsername}
                    onChange={e => setRegisterUsername(e.target.value)}
                    placeholder="Choose a username"
                    autoComplete="username"
                  />

                  <label htmlFor="register-password">Password (Optional)</label>
                  <input
                    id="register-password"
                    type="password"
                    value={registerPassword}
                    onChange={e => setRegisterPassword(e.target.value)}
                    placeholder="Create a password"
                    autoComplete="new-password"
                  />

                  <Button type="submit" disabled={busy || !registerName.trim()}>
                    {busy ? 'Creating profile…' : 'Create my local profile'} <span aria-hidden="true">→</span>
                  </Button>
                </form>
              </>
            )}

            {/* Quick 1-Click Access for Evaluators and Demos */}
            <div className="demo-credentials-box" style={{ marginTop: '20px', paddingTop: '14px', borderTop: '1px solid var(--line)' }}>
              <span className="demo-cred-label" style={{ display: 'block', fontSize: '12px', color: 'var(--muted)', marginBottom: '8px' }}>
                Quick 1-Click Demo Portals:
              </span>
              <div className="demo-cred-actions" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="button button-secondary"
                  style={{ flex: 1, fontSize: '12px', padding: '7px 10px' }}
                  onClick={() => handleQuickDemo('student')}
                  disabled={busy}
                >
                  🎓 Demo Student Portal
                </button>
                <button
                  type="button"
                  className="button button-secondary"
                  style={{ flex: 1, fontSize: '12px', padding: '7px 10px' }}
                  onClick={() => handleQuickDemo('admin')}
                  disabled={busy}
                >
                  🔬 Admin / Research Portal
                </button>
              </div>

              {/* Discreet Legacy ID Reconnect for Testing/Demos */}
              <details style={{ marginTop: '12px', fontSize: '12px', color: 'var(--muted)', textAlign: 'left' }}>
                <summary style={{ cursor: 'pointer', padding: '4px 0', opacity: 0.8 }}>Reconnect with existing Student ID</summary>
                <form onSubmit={handleReconnectProfile} style={{ marginTop: '8px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <label htmlFor="student-id" style={{ margin: 0, fontSize: '12px', whiteSpace: 'nowrap' }}>Student ID</label>
                  <input
                    id="student-id"
                    type="number"
                    min="1"
                    value={studentId}
                    onChange={e => setStudentId(e.target.value)}
                    placeholder="e.g. 1"
                    style={{ flex: 1, padding: '5px 8px', fontSize: '12px' }}
                  />
                  <Button type="submit" className="button-secondary" style={{ padding: '5px 12px', fontSize: '12px' }} disabled={busy || !studentId}>
                    Continue
                  </Button>
                </form>
              </details>
            </div>
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
            <h3>Create your profile</h3>
            <p>Get started with your student account to begin your personalized learning path.</p>
          </article>
          <article>
            <span className="learn-step-num">2</span>
            <h3>Practice and get checked</h3>
            <p>Answer questions with immediate, honest feedback. Attempts and mistakes are recorded as they happen.</p>
          </article>
          <article>
            <span className="learn-step-num">3</span>
            <h3>Master key concepts</h3>
            <p>Adaptive recommendations guide you to high-yield review topics and concept boundaries.</p>
          </article>
        </div>
      </section>

      <footer className="entry-footer">MISTIQ Learning Platform &middot; Adaptive Student Mastery</footer>
    </main>
  )
}
