import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { Icon, LoadingState, type IconName } from "../components"

const studentNav: Array<{ to: string; label: string; icon: IconName; end?: boolean }> = [
  { to: "/dashboard", label: "Dashboard", icon: "home" },
  { to: "/practice", label: "Practice", icon: "practice" },
  { to: "/mistakes", label: "Review Center", icon: "flag" },
  { to: "/progress", label: "Progress", icon: "chart" },
  { to: "/profile", label: "Profile", icon: "user" },
]

const adminNav: Array<{ to: string; label: string; icon: IconName; end?: boolean }> = [
  { to: "/research", label: "Overview", icon: "flask", end: true },
  { to: "/simulator", label: "ML Studio & Simulator", icon: "formula" },
  { to: "/research/showcase", label: "Database Showcase", icon: "database" },
  { to: "/research/formula-explorer", label: "Formula Explorer", icon: "formula" },
  { to: "/research/evaluation", label: "Model Evaluation", icon: "evaluation" },
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
  const navItems = isAdmin ? adminNav : studentNav

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <NavLink to={isAdmin ? "/research" : "/dashboard"} className="sidebar-brand" aria-label="MISTIQ home">
          <span className="brand-mark" aria-hidden="true">M</span>
          <span className="brand-copy">
            <span className="brand-name">MISTIQ</span>
            <span className="brand-tag">{isAdmin ? "Admin & Research Lab" : "Adaptive Learning"}</span>
          </span>
        </NavLink>

        <nav aria-label="Main navigation" className="side-nav">
          <span className="nav-caption">{isAdmin ? 'Admin & Research' : 'Learn'}</span>
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {!isAdmin && (
          <nav aria-label="Research navigation" className="side-nav side-nav-research">
            <span className="nav-caption">Educator &amp; Admin</span>
            <span className="nav-note">Advanced Research Lab restricted to instructors</span>
          </nav>
        )}

        {user && (
          <div className="sidebar-account">
            <span className="avatar" aria-hidden="true">{(user.name ?? user.username).slice(0, 1).toUpperCase()}</span>
            <span className="account-copy">
              <strong>{user.name ?? user.username}</strong>
              <span>{user.role === 'admin' ? 'Operator / Admin' : `Student #${user.student_id ?? ''}`}</span>
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
        {navItems.map(item => (
          <NavLink key={item.to} to={item.to} className={mobileClass} end={item.end}>
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
