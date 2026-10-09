import { Navigate, Route, Routes } from "react-router-dom"
import AppLayout from "./layouts/AppLayout"
import { DashboardPage, LoginPage, MistakesPage, PracticePage, ProgressPage, ProfilePage, ResearchPage } from "./pages/Pages"

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
<Route path="/research" element={<ResearchPage mode="overview" />} />
    <Route path="/research/showcase" element={<ResearchPage mode="showcase" />} />
    <Route path="/research/formula-explorer" element={<ResearchPage mode="formula-explorer" />} />
    <Route path="/research/analytics" element={<ResearchPage mode="analytics" />} />
    <Route path="/research/predictions" element={<ResearchPage mode="predictions" />} />
    <Route path="/research/comparisons" element={<ResearchPage mode="comparisons" />} />
  </Route>
  </Routes>
}

