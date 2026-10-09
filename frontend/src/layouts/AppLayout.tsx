import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom"
import { useStudent } from "../context/StudentContext"

export default function AppLayout() {
  const { student, ready, leave } = useStudent()
  const location = useLocation()

  if (!ready) {
    return <div className="app-shell"><main className="main-content"><div className="state"><p>Opening your learning space…</p></div></main></div>
  }
  if (!student && location.pathname !== "/login") {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">MISTIQ <span>· Intelligent Q&amp;A Practice</span></div>
        <nav className="app-nav" aria-label="Main navigation">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/practice">Practice</NavLink>
          <NavLink to="/mistakes">Mistakes</NavLink>
          <NavLink to="/progress">Progress</NavLink>
          <NavLink to="/research">Research Lab</NavLink>
          {student && (
            <button type="button" onClick={() => { leave() }} className="logout-btn">Change Student</button>
          )}
        </nav>
      </header>
      <main className="main-content"><Outlet /></main>
    </div>
  )
}

