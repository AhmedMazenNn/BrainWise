import {
  AtSignIcon,
  BriefcaseBusinessIcon,
  ShieldCheckIcon,
} from 'lucide-react'
import { Badge, Card } from '../components/ui'
import { useAuth } from '../contexts/AuthContext'

export function ProfilePage() {
  const { user } = useAuth()
  if (!user) return null

  const initials = `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase()
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username

  const roleLabel =
    user.role === 'MANAGER'
      ? 'Manager'
      : user.role === 'DISPATCHER'
        ? 'Dispatcher'
        : 'Driver'

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <p className="text-sm font-medium text-[#175e58]">Account</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
          Profile
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Your internal workspace identity and access level.
        </p>
      </div>
      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 bg-slate-50 px-6 py-7">
          <div className="flex items-center gap-4">
            <span className="grid h-14 w-14 place-items-center rounded-full bg-[#dceceb] text-lg font-bold text-[#175e58]">
              {initials}
            </span>
            <div>
              <h2 className="text-lg font-bold text-slate-900">{fullName}</h2>
              <p className="mt-1 text-sm text-slate-500">{user.email}</p>
            </div>
          </div>
        </div>
        <dl className="divide-y divide-slate-100">
          <div className="flex items-center gap-4 px-6 py-5">
            <AtSignIcon size={18} className="text-slate-400" />
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Work email
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-700">
                {user.email}
              </dd>
            </div>
          </div>
          <div className="flex items-center gap-4 px-6 py-5">
            <BriefcaseBusinessIcon size={18} className="text-slate-400" />
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Workspace role
              </dt>
              <dd className="mt-1">
                <Badge
                  tone={
                    user.role === 'MANAGER'
                      ? 'purple'
                      : user.role === 'DISPATCHER'
                        ? 'blue'
                        : 'green'
                  }
                >
                  {roleLabel}
                </Badge>
              </dd>
            </div>
          </div>
          <div className="flex items-center gap-4 px-6 py-5">
            <ShieldCheckIcon size={18} className="text-slate-400" />
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Access
              </dt>
              <dd className="mt-1 text-sm font-medium text-slate-700">
                {user.role === 'DRIVER'
                  ? 'Assigned delivery stops only'
                  : 'Full operations management'}
              </dd>
            </div>
          </div>
        </dl>
      </Card>
    </div>
  )
}
