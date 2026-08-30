import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import AppShell from './components/AppShell'
import FullScreenLoader from './components/FullScreenLoader'

const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const ClientDashboard = lazy(() => import('./pages/ClientDashboard'))
const ClientHistoryPage = lazy(() => import('./pages/ClientHistoryPage'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage'))
const AdminSimulationsPage = lazy(() => import('./pages/AdminSimulationsPage'))
const ChatWidget = lazy(() => import('./components/ChatWidget'))

export default function App() {
  return (
    <>
      <Suspense fallback={<FullScreenLoader label="Cargando interfaz" />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/client" element={<ProtectedRoute allowedRoles={["cliente", "admin"]}><AppShell /></ProtectedRoute>}>
            <Route index element={<ClientDashboard />} />
            <Route path="history" element={<ClientHistoryPage />} />
          </Route>
          <Route path="/admin" element={<ProtectedRoute allowedRoles={["admin"]}><AppShell /></ProtectedRoute>}>
            <Route index element={<AdminDashboard />} />
            <Route path="users" element={<AdminUsersPage />} />
            <Route path="simulations" element={<AdminSimulationsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Suspense>
      <Suspense fallback={null}>
        <ChatWidget />
      </Suspense>
    </>
  )
}
