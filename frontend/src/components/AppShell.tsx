import { useState } from 'react'
import {
  BellIcon,
  ClipboardListIcon,
  LayoutDashboardIcon,
  LogOutIcon,
  MenuIcon,
  RouteIcon,
  TruckIcon,
  UserRoundIcon,
  XIcon,
} from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const navItems = [
  {
    to: '/',
    label: 'Dashboard',
    icon: LayoutDashboardIcon,
    adminOnly: true,
  },
  {
    to: '/drivers',
    label: 'Drivers',
    icon: TruckIcon,
    adminOnly: true,
  },
  {
    to: '/orders',
    label: 'Orders',
    icon: ClipboardListIcon,
    adminOnly: true,
  },
  {
    to: '/runs',
    label: 'Delivery Runs',
    icon: RouteIcon,
    adminOnly: true,
  },
]

export function AppShell() {
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()

  if (!user) return null

  const isDriver = user.role === 'DRIVER'
  const links = isDriver
    ? [
        {
          to: '/runs',
          label: 'My deliveries',
          icon: RouteIcon,
          adminOnly: false,
        },
      ]
    : navItems

  const close = () => setMobileOpen(false)

  const displayName =
    user.first_name || user.username
  const initials = (
    (user.first_name?.[0] ?? '') + (user.last_name?.[0] ?? '') || user.username[0]
  ).toUpperCase()

  return (
    <div className="min-h-screen w-full bg-[#f7f8fa]">
      {mobileOpen && (
        <button
          aria-label="Close navigation"
          onClick={close}
          className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="flex h-[73px] items-center justify-between border-b border-slate-100 px-5">
          <div className="flex items-center gap-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#175e58] text-sm font-bold text-white">
              N
            </div>
            <span className="font-bold tracking-tight text-slate-900">
              Northstar
            </span>
          </div>
          <button
            onClick={close}
            aria-label="Close navigation"
            className="text-slate-400 lg:hidden"
          >
            <XIcon size={20} />
          </button>
        </div>
        <nav className="flex-1 space-y-1 p-3" aria-label="Primary navigation">
          <p className="mb-2 px-3 pt-3 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Workspace
          </p>
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={close}
              className={({ isActive }) =>
                `flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-semibold transition-colors ${isActive ? 'bg-[#e9f3f2] text-[#175e58]' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
          <p className="mb-2 mt-6 px-3 pt-3 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Account
          </p>
          <NavLink
            to="/profile"
            onClick={close}
            className={({ isActive }) =>
              `flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-semibold ${isActive ? 'bg-[#e9f3f2] text-[#175e58]' : 'text-slate-600 hover:bg-slate-50'}`
            }
          >
            <UserRoundIcon size={18} />
            Profile
          </NavLink>
        </nav>
        <div className="border-t border-slate-100 p-3">
          <button
            onClick={() => {
              logout()
              navigate('/login')
            }}
            className="flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm font-semibold text-slate-600 hover:bg-red-50 hover:text-red-700"
          >
            <LogOutIcon size={18} />
            Logout
          </button>
        </div>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-[73px] items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur md:px-7">
          <button
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
            className="rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
          >
            <MenuIcon size={21} />
          </button>
          <div className="hidden lg:block">
            <p className="text-sm font-medium text-slate-500">
              Operations workspace
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              aria-label="Notifications"
              className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100"
            >
              <BellIcon size={19} />
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-[#d97706]" />
            </button>
            <div className="h-7 w-px bg-slate-200" />
            <button
              onClick={() => navigate('/profile')}
              className="flex items-center gap-2 rounded-lg py-1 text-left"
            >
              <span className="grid h-8 w-8 place-items-center rounded-full bg-[#dceceb] text-xs font-bold text-[#175e58]">
                {initials}
              </span>
              <span className="hidden sm:block">
                <span className="block text-sm font-semibold text-slate-800">
                  {displayName}
                </span>
                <span className="block text-[11px] capitalize text-slate-500">
                  {user.role.toLowerCase()}
                </span>
              </span>
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-[1540px] p-4 md:p-7">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
