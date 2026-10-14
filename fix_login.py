path = r'C:\ML project\MISTIQ\frontend\src\pages\Pages.tsx'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    s = f.read()
# 1. remove studentcontext
s = s.replace(\"import { useStudent } from '../context/StudentContext'\\n\", '')
# 2. ensure auth
if \"useAuth\" not in s:
    s = s.replace(\"import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'\", \"import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'\\nimport { useAuth } from '../context/AuthContext'\")
# 3. replace LoginPage
# quick replace block
old_login = s[s.find('export function LoginPage'):s.find('export function DashboardPage')] if s.find('export function LoginPage')!=-1 and s.find('export function DashboardPage')!=-1 else ''
if old_login:
    new_login = '''export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, register, user } = useAuth()
  const [mode, setMode] = useState<'signin' | 'register'>('signin')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const from = (location.state as any)?.from || '/dashboard'
  useEffect(() => { if (user) navigate(from, { replace: true }) }, [user, from, navigate])
  async function handleSignIn(e: FormEvent){e.preventDefault();setBusy(true);setError('');try{await login(username,password);navigate(from,{replace:true})}catch(r){setError(errorMessage(r))}finally{setBusy(false)}}
  async function handleRegister(e: FormEvent){e.preventDefault();setBusy(true);setError('');try{await register(username,password,name||undefined);navigate(from,{replace:true})}catch(r){setError(errorMessage(r))}finally{setBusy(false)}}
  return (<div className="auth-page"><div className="auth-card"><div className="auth-header"><img src="/logo.png" alt="MISTIQ" className="auth-logo"/><div className="auth-tabs" role="tablist"><button className={mode==='signin'?'active':''} onClick={()=>setMode('signin')} role="tab">Sign in</button><button className={mode==='register'?'active':''} onClick={()=>setMode('register')} role="tab">Create account</button></div></div>{mode==='signin'?(<form onSubmit={handleSignIn} className="auth-form"><label>Username<input value={username} onChange={e=>setUsername(e.target.value)} required autoComplete="username"/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required autoComplete="current-password"/></label><button disabled={busy} type="submit">{busy?'Signing in...':'Sign in'}</button></form>):(<form onSubmit={handleRegister} className="auth-form"><label>Name (optional)<input value={name} onChange={e=>setName(e.target.value)} autoComplete="name"/></label><label>Username<input value={username} onChange={e=>setUsername(e.target.value)} required minLength={3} autoComplete="username"/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required minLength={6} autoComplete="new-password"/></label><button disabled={busy} type="submit">{busy?'Creating...':'Create account'}</button></form>)}{error&&<p className="auth-error">{error}</p>}<p className="auth-note">Admin access is controlled by environment credentials.</p></div><div className="auth-learn" id="learn-more"><h2>What is MISTIQ?</h2><p>Adaptive mathematics practice that helps you learn from mistakes.</p></div></div>)}
'''
    s = s.replace(old_login, new_login)
# 4. fix Dashboard - replace useStudent patterns
s = s.replace('const { student } = useStudent()', 'const { user } = useAuth(); const studentId = user?.student_id ?? null')
s = s.replace('if (!student) return', 'if (!studentId) return')
s = s.replace('student.id', 'studentId')
with open(path, 'w', encoding='utf-8') as f:
    f.write(s)
print('ok')
