import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import AppLayout from "./layouts/AppLayout"
import { DashboardPage, LoginPage, MistakesPage, PracticePage, ProgressPage, ProfilePage, ResearchPage } from "./pages/Pages"
import { useAuth } from "./context/AuthContext"

function RequireAdmin({ children }: { children: JSX.Element }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <></>
  if (!user || user.role !== 'admin') {
    return <Navigate to="/dashboard" replace state={{ from: location.pathname + location.search }} />
  }
  return children
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<AppLayout />}>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/practice" element={<PracticePage />} />
      <Route path="/progress" element={<ProgressPage />} />
      <Route path="/mistakes" element={<MistakesPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/research" element={<RequireAdmin><ResearchPage mode="overview" /></RequireAdmin>} />
      <Route path="/research/showcase" element={<RequireAdmin><ResearchPage mode="showcase" /></RequireAdmin>} />
      <Route path="/research/formula-explorer" element={<RequireAdmin><ResearchPage mode="formula" /></RequireAdmin>} />
      <Route path="/research/evaluation" element={<RequireAdmin><ResearchPage mode="evaluation" /></RequireAdmin>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Route>
  </Routes>
}

