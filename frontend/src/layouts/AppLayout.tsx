import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom"
import { useStudent } from "../context/StudentContext"

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: "◫" },
  { to: "/practice", label: "Practice", icon: "✎" },
  { to: "/mistakes", label: "Mistakes", icon: "⚑" },
  { to: "/progress", label: "Progress", icon: "◔" },
  { to: "/research", label: "Research Lab", icon: "⚙" },
]

export default function AppLayout() {
  const { student, ready, leave } = useStudent()
  const location = useLocation()

  if (!ready) {
    return <div className="app-shell"><main className="main-content"><div className="state"><p>Opening your learning space…</p></div></main></div>
  }
  if (!student && location.pathname !== "/login") {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />
  }

  const linkClass = ({ isActive }: { isActive: boolean }) => isActive ? "nav-link active" : "nav-link"
  const mobileClass = ({ isActive }: { isActive: boolean }) => isActive ? "mobile-link active" : "mobile-link"

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">MISTIQ <span>2.0</span></div>
        <nav aria-label="Main navigation">
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to} className={linkClass}>{item.label}</NavLink>
          ))}
        </nav>
        {student && (
          <div className="sidebar-footer">
            <div className="avatar" aria-hidden="true">{student.name.slice(0, 1).toUpperCase()}</div>
            <div className="sidebar-person"><strong>{student.name}</strong><span>Student #{student.id}</span></div>
            <button type="button" className="icon-button" title="Change student" aria-label="Change student" onClick={() => leave()}>⇥</button>
          </div>
        )}
      </aside>

      <header className="mobile-header">
        <div className="brand">MISTIQ <span>2.0</span></div>
        {student && <button type="button" className="mobile-logout" onClick={() => leave()}>Change student</button>}
      </header>

      <main className="main-content"><Outlet /></main>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        {navItems.map(item => (
          <NavLink key={item.to} to={item.to} className={mobileClass}><span aria-hidden="true">{item.icon}</span>{item.label.split(' ')[0]}</NavLink>
        ))}
      </nav>
    </div>
  )
}
