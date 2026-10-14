path = r'C:\ML project\MISTIQ\frontend\src\pages\Pages.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
# replace login function
start = content.find('export function LoginPage')
if start == -1:
    raise Exception('not found')
# find end of function - next export function
next = content.find('\nexport function ', start + 1)
if next == -1:
    next = content.find('\nexport ', start + 1)
end = next if next != -1 else len(content)
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
  async function handleSignIn(e: FormEvent){ e.preventDefault(); setBusy(true); setError(''); try{ await login(username,password); navigate(from,{replace:true}) }catch(r){ setError(errorMessage(r)) }finally{ setBusy(false) } }
  async function handleRegister(e: FormEvent){ e.preventDefault(); setBusy(true); setError(''); try{ await register(username,password,name||''); navigate(from,{replace:true}) }catch(r){ setError(errorMessage(r)) }finally{ setBusy(false) } }
  return (<div className="auth-page"><div className="auth-card"><div className="auth-header"><img src="/logo.png" alt="MISTIQ" className="auth-logo"/><div className="auth-tabs" role="tablist"><button className={mode==='signin'?'active':''} onClick={()=>setMode('signin')} role="tab">Sign in</button><button className={mode==='register'?'active':''} onClick={()=>setMode('register')} role="tab">Create account</button></div></div>{mode==='signin'?(<form onSubmit={handleSignIn} className="auth-form"><label>Username<input value={username} onChange={e=>setUsername(e.target.value)} required autoComplete="username"/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required autoComplete="current-password"/></label><button disabled={busy} type="submit">{busy?'Signing in...':'Sign in'}</button></form>):(<form onSubmit={handleRegister} className="auth-form"><label>Name (optional)<input value={name} onChange={e=>setName(e.target.value)} autoComplete="name"/></label><label>Username<input value={username} onChange={e=>setUsername(e.target.value)} required minLength={3} autoComplete="username"/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required minLength={6} autoComplete="new-password"/></label><button disabled={busy} type="submit">{busy?'Creating...':'Create account'}</button></form>)}{error&&<p className="auth-error">{error}</p>}<p className="auth-note">Admin access is controlled by environment credentials.</p></div><div className="auth-learn" id="learn-more"><h2>What is MISTIQ?</h2><p>Adaptive mathematics practice that helps you learn from mistakes.</p></div></div>)
}
'''
content = content[:start] + new_login + content[end:]
# remove any remaining useStudent references
content = content.replace('useStudent', 'useAuth')
content = content.replace('const { student } = useAuth()', 'const { user } = useAuth()')
content = content.replace('ready', '') # strip old flags
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('ok')
