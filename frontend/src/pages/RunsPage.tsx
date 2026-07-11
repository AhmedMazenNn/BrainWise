import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BanknoteIcon, ChevronRightIcon, PlayIcon, PlusIcon, Trash2Icon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
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
import type { DeliveryRun, RunStatus } from '../types/logistics'
import { useToast } from '../contexts/ToastContext'
import { useForm } from 'react-hook-form'
import axios from 'axios'

function getApiError(err: unknown): string {
  if (axios.isAxiosError(err) && err.response?.data) {
    const data = err.response.data
    if (typeof data.detail === 'string') return data.detail
  }
  return 'Something went wrong. Please try again.'
}

const tone: Record<RunStatus, 'slate' | 'blue' | 'green' | 'amber' | 'red'> = {
  DRAFT: 'slate',
  ASSIGNED: 'blue',
  EN_ROUTE: 'blue',
  COMPLETED: 'green',
  CASH_BANKED: 'amber',
  CANCELLED: 'red',
}

export function RunsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const query = useQuery({
    queryKey: ['runs'],
    queryFn: () => api.getRuns({ page_size: 100 }),
  })

  const runs = query.data?.results ?? []
  const [confirmAction, setConfirmAction] = useState<{
    run: DeliveryRun
    action: 'start' | 'bank'
  } | null>(null)
  const [building, setBuilding] = useState(false)

  const startMutation = useMutation({
    mutationFn: (id: number) => api.startRun(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Run started.')
      setConfirmAction(null)
    },
    onError: (err) => {
      showToast(getApiError(err), 'error')
    },
  })

  const bankMutation = useMutation({
    mutationFn: ({ id, location }: { id: number; location: string }) =>
      api.bankCash(id, location),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Cash banked successfully.')
      setConfirmAction(null)
    },
    onError: (err) => {
      showToast(getApiError(err), 'error')
    },
  })

  const buildMutation = useMutation({
    mutationFn: (driverId: number) => api.createRun({ driver: driverId } as Partial<DeliveryRun>),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('New delivery run created.')
      setBuilding(false)
      navigate(`/runs/${run.id}`)
    },
    onError: (err) => {
      showToast(getApiError(err), 'error')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteRun(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      showToast('Run deleted.')
    },
    onError: (err) => {
      showToast(getApiError(err), 'error')
    },
  })

  const canManage = user?.role === 'MANAGER' || user?.role === 'DISPATCHER'

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[#175e58]">
            {user?.role === 'DRIVER' ? 'Your assignments' : 'Dispatch workflow'}
          </p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Delivery runs
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {user?.role === 'DRIVER'
              ? 'Review your assigned routes and update delivery stops.'
              : 'Build, dispatch, and reconcile delivery routes.'}
          </p>
        </div>
        {canManage && (
          <Button onClick={() => setBuilding(true)}>
            <PlusIcon size={16} />
            Build run
          </Button>
        )}
      </div>

      <Card className="overflow-hidden">
        {query.isLoading ? (
          <LoadingRows />
        ) : query.isError ? (
          <ErrorState onRetry={() => query.refetch()} />
        ) : runs.length === 0 ? (
          <EmptyState
            title="No delivery runs"
            description="Build a delivery run to begin dispatching orders."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-5 py-3">Run</th>
                  <th className="px-4 py-3">Driver</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Total cash</th>
                  <th className="px-4 py-3">Started</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.map((run) => (
                  <tr key={run.id} className="text-sm">
                    <td className="px-5 py-4">
                      <p className="font-mono-ui text-xs font-semibold text-slate-700">
                        RUN-{run.id}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {run.stops_count ?? 0} stops
                      </p>
                    </td>
                    <td className="px-4 py-4 font-semibold text-slate-700">
                      {run.driver_name}
                    </td>
                    <td className="px-4 py-4">
                      <Badge tone={tone[run.status]}>
                        {run.status.replace('_', ' ')}
                      </Badge>
                    </td>
                    <td className="px-4 py-4 font-semibold text-slate-700">
                      ${Number(run.total_cash_collected).toLocaleString()}
                    </td>
                    <td className="px-4 py-4 text-slate-500">
                      {run.started_at
                        ? new Date(run.started_at).toLocaleString()
                        : 'Not started'}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => navigate(`/runs/${run.id}`)}
                          className="inline-flex items-center gap-1 font-semibold text-[#175e58] hover:underline"
                        >
                          View <ChevronRightIcon size={15} />
                        </button>
                        {canManage && run.status === 'DRAFT' && (
                          <button
                            aria-label={`Delete RUN-${run.id}`}
                            onClick={() => deleteMutation.mutate(run.id)}
                            className="rounded-md p-1.5 text-red-600 hover:bg-red-50"
                          >
                            <Trash2Icon size={16} />
                          </button>
                        )}
                        {canManage && run.status === 'ASSIGNED' && (
                          <button
                            aria-label={`Start RUN-${run.id}`}
                            onClick={() =>
                              setConfirmAction({ run, action: 'start' })
                            }
                            className="rounded-md p-1.5 text-sky-700 hover:bg-sky-50"
                          >
                            <PlayIcon size={16} />
                          </button>
                        )}
                        {canManage && run.status === 'COMPLETED' && (
                          <button
                            aria-label={`Bank cash for RUN-${run.id}`}
                            onClick={() =>
                              setConfirmAction({ run, action: 'bank' })
                            }
                            className="rounded-md p-1.5 text-amber-700 hover:bg-amber-50"
                          >
                            <BanknoteIcon size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {building && (
        <BuildRunModal
          loading={buildMutation.isPending}
          onClose={() => setBuilding(false)}
          onConfirm={(driverId) => buildMutation.mutate(driverId)}
        />
      )}

      {confirmAction?.action === 'start' && (
        <ConfirmDialog
          title="Start this run?"
          description={`Dispatch RUN-${confirmAction.run.id} to ${confirmAction.run.driver_name}.`}
          confirmText="Start run"
          loading={startMutation.isPending}
          onClose={() => setConfirmAction(null)}
          onConfirm={() => startMutation.mutate(confirmAction.run.id)}
        />
      )}

      {confirmAction?.action === 'bank' && (
        <BankCashModal
          run={confirmAction.run}
          loading={bankMutation.isPending}
          onClose={() => setConfirmAction(null)}
          onConfirm={(location) =>
            bankMutation.mutate({ id: confirmAction.run.id, location })
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
  onConfirm: (driverId: number) => void
}) {
  const driversQuery = useQuery({
    queryKey: ['available-drivers'],
    queryFn: () => api.getAvailableDrivers({ page_size: 100 }),
  })

  const drivers = driversQuery.data?.results ?? []
  const [selectedDriver, setSelectedDriver] = useState<number | null>(null)

  return (
    <Modal title="Build delivery run" onClose={onClose}>
      <div className="space-y-4 p-5">
        <p className="text-sm text-slate-600">
          Select an available driver to create a new draft run.
        </p>
        <Field label="Assign driver">
          {driversQuery.isLoading ? (
            <div className="h-10 animate-pulse rounded-lg bg-slate-100" />
          ) : (
            <select
              className={inputClass}
              value={selectedDriver ?? ''}
              onChange={(e) => setSelectedDriver(Number(e.target.value) || null)}
            >
              <option value="">Select a driver...</option>
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          )}
        </Field>
        {drivers.length === 0 && !driversQuery.isLoading && (
          <p className="text-sm text-amber-600">No available drivers found.</p>
        )}
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={loading}
            disabled={!selectedDriver}
            onClick={() => selectedDriver && onConfirm(selectedDriver)}
          >
            Create run
          </Button>
        </div>
      </div>
    </Modal>
  )
}

function BankCashModal({
  run,
  loading,
  onClose,
  onConfirm,
}: {
  run: DeliveryRun
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
        <p className="text-sm text-slate-600">
          Confirm that ${Number(run.total_cash_collected).toLocaleString()} from
          RUN-{run.id} has been banked.
        </p>
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
