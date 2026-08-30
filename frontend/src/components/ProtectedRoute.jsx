import { Navigate } from 'react-router-dom'
import { useAuth } from '../state/AuthContext'
import FullScreenLoader from './FullScreenLoader'

export default function ProtectedRoute({ allowedRoles, children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <FullScreenLoader label="Validando acceso" />
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (!allowedRoles.includes(user.rol)) {
    return <Navigate to={user.rol === 'admin' ? '/admin' : '/client'} replace />
  }

  return children
}
