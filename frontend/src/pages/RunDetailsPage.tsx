import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeftIcon,
  CheckCircle2Icon,
  MapPinIcon,
  PlusIcon,
  Trash2Icon,
  XCircleIcon,
} from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  inputClass,
  LoadingRows,
  Modal,
} from '../components/ui'
import { api } from '../data/api'
import { useAuth } from '../contexts/AuthContext'
import type { DeliveryStop, RunStatus, StopStatus } from '../types/logistics'
import { useToast } from '../contexts/ToastContext'
import { useForm } from 'react-hook-form'
import axios from 'axios'

const runTone: Record<RunStatus, 'slate' | 'blue' | 'green' | 'amber' | 'red'> = {
  DRAFT: 'slate',
  ASSIGNED: 'blue',
  EN_ROUTE: 'blue',
  COMPLETED: 'green',
  CASH_BANKED: 'amber',
  CANCELLED: 'red',
}

const stopTone: Record<StopStatus, 'slate' | 'green' | 'red' | 'blue'> = {
  ASSIGNED: 'slate',
  EN_ROUTE: 'blue',
  DELIVERED: 'green',
  FAILED: 'red',
}

function getApiError(err: unknown): string {
  if (axios.isAxiosError(err) && err.response?.data) {
    const data = err.response.data
    if (typeof data.detail === 'string') return data.detail
    if (data.detail && typeof data.detail === 'object') {
      const messages = Object.values(data.detail)
        .flat()
        .map((v) => String(v))
      return messages.join(', ')
    }
  }
  return 'Something went wrong. Please try again.'
}

export function RunDetailsPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const runQuery = useQuery({
    queryKey: ['run', id],
    queryFn: () => api.getRun(Number(id)),
  })

  const stopsQuery = useQuery({
    queryKey: ['stops', id],
    queryFn: () => api.getStops({ delivery_run: id, page_size: 100 }),
    enabled: !!runQuery.data,
  })

  const [confirmAction, setConfirmAction] = useState<string | null>(null)
  const [failedStop, setFailedStop] = useState<DeliveryStop | null>(null)
  const [building, setBuilding] = useState(false)

  const startMutation = useMutation({
    mutationFn: () => api.startRun(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run', id] })
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Run started.')
      setConfirmAction(null)
    },
    onError: (err) => showToast(getApiError(err), 'error'),
  })

  const completeMutation = useMutation({
    mutationFn: () => api.completeRun(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run', id] })
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Run completed.')
      setConfirmAction(null)
    },
    onError: (err) => showToast(getApiError(err), 'error'),
  })

  const bankMutation = useMutation({
    mutationFn: (location: string) => api.bankCash(Number(id), location),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run', id] })
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Cash banked successfully.')
      setConfirmAction(null)
    },
    onError: (err) => showToast(getApiError(err), 'error'),
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteRun(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Run deleted.')
      navigate('/runs')
    },
    onError: (err) => showToast(getApiError(err), 'error'),
  })

  const buildMutation = useMutation({
    mutationFn: (orderIds: number[]) => api.buildRun(Number(id), orderIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run', id] })
      queryClient.invalidateQueries({ queryKey: ['stops', id] })
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Run built successfully. Orders assigned.')
      setBuilding(false)
    },
    onError: (err) => showToast(getApiError(err), 'error'),
  })

  const deliverMutation = useMutation({
    mutationFn: (stopId: number) => api.markDelivered(stopId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stops', id] })
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Stop marked delivered.')
    },
    onError: (err) => showToast(getApiError(err), 'error'),
  })

  const failMutation = useMutation({
    mutationFn: ({ stopId, reason }: { stopId: number; reason: string }) =>
      api.markFailed(stopId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stops', id] })
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Stop marked failed.')
      setFailedStop(null)
    },
    onError: (err) => showToast(getApiError(err), 'error'),
  })

  if (runQuery.isLoading) return <LoadingRows />
  if (runQuery.isError) return <ErrorState onRetry={() => runQuery.refetch()} />
  const run = runQuery.data
  if (!run)
    return (
      <EmptyState
        title="Run not found"
        description="This delivery run may have been removed."
      />
    )

  const stops = stopsQuery.data?.results ?? []
  const canManage = user?.role === 'MANAGER' || user?.role === 'DISPATCHER'
  const isDriver = user?.role === 'DRIVER'
  const completedStops = stops.filter(
    (s) => s.status === 'DELIVERED' || s.status === 'FAILED',
  ).length
  const allStopsDone = stops.length > 0 && completedStops === stops.length

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/runs')}
        className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-[#175e58]"
      >
        <ArrowLeftIcon size={16} />
        Back to delivery runs
      </button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono-ui text-xs font-semibold text-slate-500">
            RUN-{run.id}
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
            {isDriver ? 'My delivery route' : 'Delivery run details'}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {run.driver_name} · {stops.length} ordered stops
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={runTone[run.status]}>
            {run.status.replace('_', ' ')}
          </Badge>
          {canManage && run.status === 'DRAFT' && (
            <>
              <Button onClick={() => setBuilding(true)}>
                <PlusIcon size={16} />
                Add orders
              </Button>
              <Button
                variant="danger"
                onClick={() => setConfirmAction('delete')}
              >
                <Trash2Icon size={16} />
                Delete
              </Button>
            </>
          )}
          {canManage && run.status === 'ASSIGNED' && (
            <Button onClick={() => setConfirmAction('start')}>Start run</Button>
          )}
          {canManage && run.status === 'EN_ROUTE' && (
            <Button
              disabled={!allStopsDone}
              onClick={() => setConfirmAction('complete')}
              title={
                allStopsDone
                  ? 'Complete this run'
                  : 'All stops must be delivered or failed first'
              }
            >
              Complete run
            </Button>
          )}
          {canManage && run.status === 'COMPLETED' && (
            <Button onClick={() => setConfirmAction('bank')}>Bank cash</Button>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Driver
          </p>
          <p className="mt-2 font-bold text-slate-800">{run.driver_name}</p>
          <p className="mt-1 text-sm text-slate-500">
            Assigned delivery driver
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Collected cash
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
            ${Number(run.total_cash_collected).toLocaleString()}
          </p>
          {run.cash_banked_location && (
            <p className="mt-1 text-sm text-slate-500">
              Banked at {run.cash_banked_location}
            </p>
          )}
        </Card>
        <Card className="p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Stop progress
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
            {completedStops}/{stops.length}
          </p>
          <div className="mt-3 h-1.5 rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-[#175e58]"
              style={{
                width: `${stops.length ? (completedStops / stops.length) * 100 : 0}%`,
              }}
            />
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="font-bold text-slate-800">Delivery stops</h2>
          <p className="mt-1 text-xs text-slate-500">
            Stops are ordered by route sequence.
          </p>
        </div>
        {stops.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-slate-500">
              No stops yet.{' '}
              {canManage && run.status === 'DRAFT' && (
                <button
                  onClick={() => setBuilding(true)}
                  className="font-semibold text-[#175e58] hover:underline"
                >
                  Add orders
                </button>
              )}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {stops.map((stop) => (
              <div
                className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center"
                key={stop.id}
              >
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#e9f3f2] text-sm font-bold text-[#175e58]">
                  {stop.stop_sequence}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-slate-800">
                    {stop.customer_name}
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500">
                    <MapPinIcon size={14} />
                    {stop.address}
                  </p>
                  {stop.failed_reason && (
                    <p className="mt-1 text-xs text-red-600">
                      Reason: {stop.failed_reason}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-4 sm:ml-auto">
                  <div className="text-right">
                    <p className="font-semibold text-slate-800">
                      ${Number(stop.cash_amount).toLocaleString()}
                    </p>
                    <Badge tone={stopTone[stop.status]}>
                      {stop.status.replace('_', ' ')}
                    </Badge>
                  </div>
                  {(isDriver || canManage) &&
                    (stop.status === 'ASSIGNED' || stop.status === 'EN_ROUTE') && (
                      <div className="flex gap-2">
                        <Button
                          loading={deliverMutation.isPending}
                          className="h-9"
                          onClick={() => deliverMutation.mutate(stop.id)}
                        >
                          <CheckCircle2Icon size={15} />
                          Delivered
                        </Button>
                        <Button
                          loading={failMutation.isPending}
                          variant="secondary"
                          className="h-9 border-red-100 text-red-700 hover:bg-red-50"
                          onClick={() => setFailedStop(stop)}
                        >
                          <XCircleIcon size={15} />
                          Failed
                        </Button>
                      </div>
                    )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {confirmAction === 'start' && (
        <ConfirmDialog
          title="Start delivery run?"
          description="The driver will be notified that this route is ready."
          confirmText="Start run"
          loading={startMutation.isPending}
          onClose={() => setConfirmAction(null)}
          onConfirm={() => startMutation.mutate()}
        />
      )}

      {confirmAction === 'complete' && (
        <ConfirmDialog
          title="Complete delivery run?"
          description="Confirm all route work is complete before closing this run."
          confirmText="Complete run"
          loading={completeMutation.isPending}
          onClose={() => setConfirmAction(null)}
          onConfirm={() => completeMutation.mutate()}
        />
      )}

      {confirmAction === 'bank' && (
        <BankCashModal
          loading={bankMutation.isPending}
          onClose={() => setConfirmAction(null)}
          onConfirm={(location) => bankMutation.mutate(location)}
        />
      )}

      {confirmAction === 'delete' && (
        <ConfirmDialog
          title="Delete this run?"
          description="This will permanently delete this draft run. This cannot be undone."
          confirmText="Delete run"
          loading={deleteMutation.isPending}
          onClose={() => setConfirmAction(null)}
          onConfirm={() => deleteMutation.mutate()}
        />
      )}

      {building && (
        <BuildRunModal
          loading={buildMutation.isPending}
          onClose={() => setBuilding(false)}
          onConfirm={(orderIds) => buildMutation.mutate(orderIds)}
        />
      )}

      {failedStop && (
        <FailReasonModal
          loading={failMutation.isPending}
          onClose={() => setFailedStop(null)}
          onConfirm={(reason) =>
            failMutation.mutate({ stopId: failedStop.id, reason })
          }
        />
      )}
    </div>
  )
}

function BuildRunModal({
  loading,
  onClose,
  onConfirm,
}: {
  loading: boolean
  onClose: () => void
  onConfirm: (orderIds: number[]) => void
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const ordersQuery = useQuery({
    queryKey: ['open-orders'],
    queryFn: () => api.getOrders({ status: 'OPEN', page_size: 100 }),
  })

  const orders = ordersQuery.data?.results ?? []

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (selected.size === orders.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(orders.map((o) => o.id)))
    }
  }

  return (
    <Modal title="Add orders to run" onClose={onClose}>
      <div className="space-y-4 p-5">
        <p className="text-sm text-slate-600">
          Select open orders to assign as delivery stops.
        </p>

        {ordersQuery.isLoading ? (
          <LoadingRows />
        ) : orders.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">
            No open orders available.
          </p>
        ) : (
          <>
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <input
                type="checkbox"
                checked={selected.size === orders.length && orders.length > 0}
                onChange={toggleAll}
                className="h-4 w-4 accent-[#175e58]"
              />
              <span className="text-xs font-semibold text-slate-500">
                Select all ({orders.length})
              </span>
              {selected.size > 0 && (
                <span className="ml-auto text-xs text-slate-400">
                  {selected.size} selected
                </span>
              )}
            </div>

            <div className="max-h-72 space-y-1 overflow-y-auto">
              {orders.map((order) => (
                <label
                  key={order.id}
                  className="flex cursor-pointer items-start gap-3 rounded-lg p-3 hover:bg-slate-50"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(order.id)}
                    onChange={() => toggle(order.id)}
                    className="mt-0.5 h-4 w-4 accent-[#175e58]"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono-ui text-xs font-semibold text-slate-600">
                        ORD-{order.id}
                      </span>
                      <Badge
                        tone={
                          order.priority === 'HIGH'
                            ? 'red'
                            : order.priority === 'MEDIUM'
                              ? 'amber'
                              : 'slate'
                        }
                      >
                        {order.priority}
                      </Badge>
                    </div>
                    <p className="mt-0.5 text-sm font-medium text-slate-800">
                      {order.customer_name}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-slate-500">
                      {order.address}
                    </p>
                  </div>
                  <span className="shrink-0 text-sm font-semibold text-slate-700">
                    ${Number(order.cash_amount).toLocaleString()}
                  </span>
                </label>
              ))}
            </div>
          </>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={loading}
            disabled={selected.size === 0}
            onClick={() => onConfirm(Array.from(selected))}
          >
            Add {selected.size > 0 ? `(${selected.size})` : ''} orders
          </Button>
        </div>
      </div>
    </Modal>
  )
}

function BankCashModal({
  loading,
  onClose,
  onConfirm,
}: {
  loading: boolean
  onClose: () => void
  onConfirm: (location: string) => void
}) {
  const { register, handleSubmit } = useForm<{ location: string }>({
    defaultValues: { location: '' },
  })

  return (
    <Modal title="Bank collected cash" onClose={onClose}>
      <form
        onSubmit={handleSubmit((values) => onConfirm(values.location))}
        className="space-y-4 p-5"
      >
        <Field label="Bank / cash drop location">
          <input
            className={inputClass}
            placeholder="e.g. Main branch, ATM deposit"
            {...register('location', { required: 'Location is required' })}
          />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Bank cash
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function FailReasonModal({
  loading,
  onClose,
  onConfirm,
}: {
  loading: boolean
  onClose: () => void
  onConfirm: (reason: string) => void
}) {
  const { register, handleSubmit } = useForm<{ reason: string }>({
    defaultValues: { reason: '' },
  })

  return (
    <Modal title="Mark stop as failed" onClose={onClose}>
      <form
        onSubmit={handleSubmit((values) => onConfirm(values.reason))}
        className="space-y-4 p-5"
      >
        <Field label="Failure reason">
          <input
            className={inputClass}
            placeholder="e.g. Customer not available, wrong address"
            {...register('reason', { required: 'Reason is required' })}
          />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="danger" loading={loading}>
            Mark failed
          </Button>
        </div>
      </form>
    </Modal>
  )
}
