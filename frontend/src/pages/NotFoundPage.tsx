import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui'

export function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <p className="font-mono-ui text-6xl font-bold text-slate-300">404</p>
      <h1 className="mt-4 text-2xl font-bold text-slate-900">Page not found</h1>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Button className="mt-6" onClick={() => navigate('/')}>
        Go to dashboard
      </Button>
    </div>
  )
}
