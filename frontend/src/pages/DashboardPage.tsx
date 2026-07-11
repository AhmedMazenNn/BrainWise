
import { useQuery } from '@tanstack/react-query'
import {
  ClipboardListIcon,
  RouteIcon,
  TruckIcon,
  UserRoundPlusIcon,
  WalletCardsIcon,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Badge, Button, Card, LoadingRows } from '../components/ui'
import { api } from '../data/api'
import { useAuth } from '../contexts/AuthContext'
import type { DeliveryRun } from '../types/logistics'

const statusTone: Record<string, 'green' | 'amber' | 'slate' | 'blue'> = {
  DRAFT: 'slate',
  EN_ROUTE: 'blue',
  COMPLETED: 'green',
  CASH_BANKED: 'amber',
}

function StatCard({
  label,
  value,
  icon: Icon,
  note,
}: {
  label: string
  value: string | number
  icon: typeof TruckIcon
  note: string
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            {label}
          </p>
          <p className="mt-3 text-2xl font-bold tracking-tight text-slate-900">
            {value}
          </p>
          <p className="mt-1 text-xs text-slate-500">{note}</p>
        </div>
        <div className="rounded-lg bg-[#e9f3f2] p-2.5 text-[#175e58]">
          <Icon size={19} />
        </div>
      </div>
    </Card>
  )
}

function MiniChart({
  title,
  items,
  colors,
}: {
  title: string
  items: { label: string; value: number }[]
  colors: string[]
}) {
  const max = Math.max(...items.map((item) => item.value), 1)
  return (
    <Card className="p-5">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="font-bold text-slate-800">{title}</h2>
      </div>
      <div className="space-y-4">
        {items.map((item, index) => (
          <div key={item.label}>
            <div className="mb-1.5 flex justify-between text-xs">
              <span className="font-medium text-slate-600">{item.label}</span>
              <span className="font-mono-ui text-slate-500">{item.value}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full ${colors[index]}`}
                style={{ width: `${(item.value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function RunRow({ run, onView }: { run: DeliveryRun; onView: () => void }) {
  return (
    <tr className="text-sm">
      <td className="px-5 py-4 font-mono-ui text-xs font-semibold text-slate-700">
        #{run.id}
      </td>
      <td className="px-4 py-4 font-medium text-slate-700">{run.driver_name}</td>
      <td className="px-4 py-4 text-slate-600">{run.stops_count ?? 0}</td>
      <td className="px-4 py-4">
        <Badge tone={statusTone[run.status] ?? 'slate'}>
          {run.status.replace('_', ' ').toLowerCase()}
        </Badge>
      </td>
      <td className="px-4 py-4 font-medium text-slate-700">
        ${Number(run.total_cash_collected).toLocaleString()}
      </td>
      <td className="px-5 py-4 text-right">
        <button
          onClick={onView}
          className="font-semibold text-[#175e58] hover:underline"
        >
          View
        </button>
      </td>
    </tr>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const runsQuery = useQuery({
    queryKey: ['runs'],
    queryFn: () => api.getRuns({ page_size: 100 }),
  })
  const driversQuery = useQuery({
    queryKey: ['drivers'],
    queryFn: () => api.getDrivers({ page_size: 100 }),
  })
  const ordersQuery = useQuery({
    queryKey: ['orders'],
    queryFn: () => api.getOrders({ page_size: 100 }),
  })

  if (user?.role === 'DRIVER') return <DriverDashboard />

  const runs = runsQuery.data?.results ?? []
  const drivers = driversQuery.data?.results ?? []
  const orders = ordersQuery.data?.results ?? []

  const activeRuns = runs.filter((run) => run.status === 'EN_ROUTE')
  const openOrders = orders.filter((o) => o.status === 'OPEN')
  const activeDrivers = drivers.filter((d) => d.active && d.status !== 'INACTIVE')
  const onRunDrivers = drivers.filter((d) => d.status === 'ON_RUN')

  const totalCash = runs.reduce(
    (sum, r) => sum + Number(r.total_cash_collected),
    0,
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[#175e58]">Today</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Operations overview
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Live delivery performance across your network.
          </p>
        </div>
        <Button onClick={() => navigate('/orders')}>Create order</Button>
      </div>

      {runsQuery.isLoading || driversQuery.isLoading || ordersQuery.isLoading ? (
        <LoadingRows />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard
              label="Open orders"
              value={openOrders.length}
              icon={ClipboardListIcon}
              note="Awaiting assignment"
            />
            <StatCard
              label="Active drivers"
              value={activeDrivers.length}
              icon={TruckIcon}
              note="Available in fleet"
            />
            <StatCard
              label="Drivers on run"
              value={onRunDrivers.length}
              icon={UserRoundPlusIcon}
              note="Currently delivering"
            />
            <StatCard
              label="Runs en route"
              value={activeRuns.length}
              icon={RouteIcon}
              note="Out for delivery"
            />
            <StatCard
              label="Completed"
              value={runs.filter((r) => r.status === 'COMPLETED').length}
              icon={RouteIcon}
              note="Successful runs"
            />
            <StatCard
              label="Cash collected"
              value={`$${totalCash.toLocaleString()}`}
              icon={WalletCardsIcon}
              note="Across all runs"
            />
          </div>

          <div className="grid gap-5 xl:grid-cols-3">
            <MiniChart
              title="Orders by status"
              items={[
                { label: 'Open', value: openOrders.length },
                { label: 'Assigned', value: orders.filter((o) => o.status === 'ASSIGNED').length },
                { label: 'En Route', value: orders.filter((o) => o.status === 'EN_ROUTE').length },
                { label: 'Delivered', value: orders.filter((o) => o.status === 'DELIVERED').length },
                { label: 'Failed', value: orders.filter((o) => o.status === 'FAILED').length },
              ]}
              colors={['bg-[#175e58]', 'bg-sky-500', 'bg-blue-500', 'bg-emerald-500', 'bg-red-500']}
            />
            <MiniChart
              title="Run health"
              items={[
                { label: 'En route', value: activeRuns.length },
                { label: 'Completed', value: runs.filter((r) => r.status === 'COMPLETED').length },
                { label: 'Draft', value: runs.filter((r) => r.status === 'DRAFT').length },
              ]}
              colors={['bg-sky-500', 'bg-emerald-500', 'bg-slate-400']}
            />

            <Card className="overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                <div>
                  <h2 className="font-bold text-slate-800">Recent runs</h2>
                  <p className="mt-0.5 text-xs text-slate-500">Latest delivery runs</p>
                </div>
                <Button
                  variant="secondary"
                  className="h-8"
                  onClick={() => navigate('/runs')}
                >
                  View all
                </Button>
              </div>
              {runs.length === 0 ? (
                <EmptyStateInline title="No runs yet" description="Build a delivery run to get started." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[500px] text-left">
                    <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                      <tr>
                        <th className="px-5 py-3 font-semibold">Run</th>
                        <th className="px-4 py-3 font-semibold">Driver</th>
                        <th className="px-4 py-3 font-semibold">Status</th>
                        <th className="px-4 py-3 font-semibold">Cash</th>
                        <th className="px-5 py-3" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {runs.slice(0, 5).map((run) => (
                        <RunRow
                          run={run}
                          onView={() => navigate(`/runs/${run.id}`)}
                          key={run.id}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

function EmptyStateInline({ title, description }: { title: string; description: string }) {
  return (
    <div className="px-5 py-10 text-center">
      <p className="font-semibold text-slate-700">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
    </div>
  )
}

function DriverDashboard() {
  const navigate = useNavigate()

  const runsQuery = useQuery({
    queryKey: ['driver-runs'],
    queryFn: () => api.getRuns({ page_size: 100 }),
  })

  const stopsQuery = useQuery({
    queryKey: ['driver-stops'],
    queryFn: () => api.getStops({ page_size: 100 }),
  })

  const runs = runsQuery.data?.results ?? []
  const stops = stopsQuery.data?.results ?? []
  const activeRun = runs.find((r) => r.status === 'EN_ROUTE')
  const myStops = activeRun
    ? stops.filter((s) => s.delivery_run === activeRun.id)
    : []

  return (
    <div>
      <p className="text-sm font-medium text-[#175e58]">Your route</p>
      <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
        Today's deliveries
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Complete each stop to keep your route moving.
      </p>
      {runsQuery.isLoading ? (
        <LoadingRows />
      ) : activeRun ? (
        <Card className="mt-6 overflow-hidden">
          <div className="border-b border-slate-100 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-mono-ui text-xs font-semibold text-slate-500">
                  #{activeRun.id}
                </p>
                <h2 className="mt-1 text-lg font-bold">
                  {myStops.length} assigned stops
                </h2>
              </div>
              <Badge tone="blue">en route</Badge>
            </div>
          </div>
          <div className="divide-y divide-slate-100">
            {myStops.map((stop) => (
              <button
                onClick={() => navigate(`/runs/${activeRun.id}`)}
                className="flex w-full items-center gap-4 p-5 text-left hover:bg-slate-50"
                key={stop.id}
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#e9f3f2] text-sm font-bold text-[#175e58]">
                  {stop.stop_sequence}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-slate-800">
                    {stop.customer_name}
                  </span>
                  <span className="mt-0.5 block truncate text-sm text-slate-500">
                    {stop.address}
                  </span>
                </span>
                <span className="font-semibold text-slate-700">
                  ${Number(stop.cash_amount).toLocaleString()}
                </span>
              </button>
            ))}
          </div>
        </Card>
      ) : (
        <Card className="mt-6 p-10 text-center">
          <p className="font-semibold text-slate-700">No active route assigned</p>
          <p className="mt-1 text-sm text-slate-500">
            Check back with dispatch for your next delivery run.
          </p>
        </Card>
      )}
    </div>
  )
}
