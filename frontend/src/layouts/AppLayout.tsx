import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { Icon, LoadingState, type IconName } from "../components"

const studentNav: Array<{ to: string; label: string; icon: IconName }> = [
  { to: "/dashboard", label: "Dashboard", icon: "home" },
  { to: "/practice", label: "Practice", icon: "practice" },
  { to: "/mistakes", label: "Mistakes", icon: "flag" },
  { to: "/progress", label: "Progress", icon: "chart" },
  { to: "/profile", label: "Profile", icon: "user" },
]

const mobileNavStudent: Array<{ to: string; label: string; icon: IconName }> = [
  { to: "/dashboard", label: "Dashboard", icon: "home" },
  { to: "/practice", label: "Practice", icon: "practice" },
  { to: "/mistakes", label: "Mistakes", icon: "flag" },
  { to: "/progress", label: "Progress", icon: "chart" },
  { to: "/profile", label: "Profile", icon: "user" },
]

export default function AppLayout() {
  const { user, ready, logout } = useAuth()
  const location = useLocation()

  if (!ready) {
    return <div className="app-shell"><main className="app-main"><div className="app-content"><LoadingState label="Opening your learning space…" /></div></main></div>
  }
  if (!user && location.pathname !== "/login") {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />
  }

  const linkClass = ({ isActive }: { isActive: boolean }) => isActive ? "nav-link active" : "nav-link"
  const mobileClass = ({ isActive }: { isActive: boolean }) => isActive ? "mobile-link active" : "mobile-link"

  const isAdmin = user?.role === 'admin'
  const mobileNav = isAdmin
    ? [
        { to: "/research", label: "Overview", icon: "flask" as IconName },
        { to: "/research/showcase", label: "Database", icon: "database" as IconName },
        { to: "/research/formula-explorer", label: "Formula", icon: "formula" as IconName },
        { to: "/research/evaluation", label: "Evaluation", icon: "evaluation" as IconName },
      ]
    : mobileNavStudent

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <NavLink to={isAdmin ? "/research" : "/dashboard"} className="sidebar-brand" aria-label="MISTIQ home">
          <span className="brand-mark" aria-hidden="true">M</span>
          <span className="brand-copy">
            <span className="brand-name">MISTIQ</span>
            <span className="brand-tag">Mistake Intelligence</span>
          </span>
        </NavLink>

        <nav aria-label="Main navigation" className="side-nav">
          <span className="nav-caption">{isAdmin ? 'Admin' : 'Learn'}</span>
          {isAdmin ? (
            <>
              <NavLink to="/research" end className={linkClass}><Icon name="flask" /><span>Overview</span></NavLink>
              <NavLink to="/research/showcase" className={linkClass}><Icon name="database" /><span>Database</span></NavLink>
              <NavLink to="/research/formula-explorer" className={linkClass}><Icon name="formula" /><span>Formula explorer</span></NavLink>
              <NavLink to="/research/evaluation" className={linkClass}><Icon name="evaluation" /><span>Evaluation</span></NavLink>
            </>
          ) : (
            studentNav.map(item => (
              <NavLink key={item.to} to={item.to} className={linkClass}>
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </NavLink>
            ))
          )}
        </nav>

        {!isAdmin && (
          <nav aria-label="Research navigation" className="side-nav side-nav-research">
            <span className="nav-caption">Research</span>
            <span className="nav-note">Operator access required</span>
          </nav>
        )}

        {user && (
          <div className="sidebar-account">
            <span className="avatar" aria-hidden="true">{(user.name ?? user.username).slice(0, 1).toUpperCase()}</span>
            <span className="account-copy">
              <strong>{user.name ?? user.username}</strong>
              <span>{user.role === 'admin' ? 'Operator' : `Student #${user.student_id ?? ''}`}</span>
            </span>
            <button type="button" className="sidebar-logout" onClick={() => logout()}>Sign out</button>
          </div>
        )}
      </aside>

      <header className="mobile-header">
        <NavLink to={isAdmin ? "/research" : "/dashboard"} className="sidebar-brand" aria-label="MISTIQ home">
          <span className="brand-mark" aria-hidden="true">M</span>
          <span className="brand-copy"><span className="brand-name">MISTIQ</span></span>
        </NavLink>
        <div className="mobile-actions">
          {!isAdmin && user && (
            <NavLink to="/profile" className={({ isActive }) => isActive ? "icon-action active" : "icon-action"} aria-label="Your learning profile">
              <Icon name="user" />
            </NavLink>
          )}
          {user && <button type="button" className="sidebar-logout" onClick={() => logout()}>Sign out</button>}
        </div>
      </header>

      <main className="app-main"><div className="app-content"><Outlet /></div></main>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        {mobileNav.map(item => (
          <NavLink key={item.to} to={item.to} className={mobileClass} end={item.to === '/research'}>
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
