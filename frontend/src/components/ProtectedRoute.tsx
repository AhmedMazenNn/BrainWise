
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  if (isLoading)
    return (
      <div className="grid min-h-screen place-items-center bg-slate-50 text-sm font-medium text-slate-500">
        Loading workspace…
      </div>
    )
  return user ? <Outlet /> : <Navigate to="/login" replace />
}
