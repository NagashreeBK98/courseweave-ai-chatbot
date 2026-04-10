import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import './index.css'

import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import AppShell from './components/layout/AppShell'
import DashboardPage from './pages/DashboardPage'
import AdvisorPage from './pages/AdvisorPage'
import CatalogPage from './pages/CatalogPage'
import RoadmapPage from './pages/RoadmapPage'
import PrerequisitesPage from './pages/PrerequisitesPage'
import ProgressPage from './pages/ProgressPage'

function PrivateRoute({ children }) {
  const { student, loading } = useAuth()
  if (loading) return <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100vh', color:'var(--text-secondary)', fontFamily:'var(--font)' }}>Loading…</div>
  return student ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { student, loading } = useAuth()
  if (loading) return null
  return student ? <Navigate to="/dashboard" replace /> : children
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<PublicRoute><LandingPage /></PublicRoute>} />
          <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/signup" element={<PublicRoute><SignupPage /></PublicRoute>} />
          <Route path="/" element={<PrivateRoute><AppShell /></PrivateRoute>}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="advisor" element={<AdvisorPage />} />
            <Route path="catalog" element={<CatalogPage />} />
            <Route path="roadmap" element={<RoadmapPage />} />
            <Route path="prerequisites" element={<PrerequisitesPage />} />
            <Route path="progress" element={<ProgressPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
