import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Edit3Icon, PlusIcon, Trash2Icon } from 'lucide-react'
import { useForm } from 'react-hook-form'
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
  Pagination,
  SearchInput,
} from '../components/ui'
import { api } from '../data/api'
import type { Driver } from '../types/logistics'
import { useToast } from '../contexts/ToastContext'

type DriverForm = {
  name: string
  email: string
  phone_number: string
  max_stops_per_run: number
  active: boolean
}

export function DriversPage() {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Driver | null | undefined>(undefined)
  const [removing, setRemoving] = useState<Driver | null>(null)

  const query = useQuery({
    queryKey: ['drivers', { search, status, page }],
    queryFn: () => {
      const params: Record<string, string | number> = { page, page_size: 5 }
      if (search) params.search = search
      if (status !== 'all') params.status = status
      return api.getDrivers(params)
    },
  })

  const drivers = query.data?.results ?? []
  const total = query.data?.count ?? 0

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteDriver(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drivers'] })
      showToast('Driver removed from fleet.')
      setRemoving(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[#175e58]">Fleet management</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">Drivers</h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage delivery personnel and fleet availability.
          </p>
        </div>
        <Button onClick={() => setEditing(null)}>
          <PlusIcon size={16} />
          Add driver
        </Button>
      </div>
      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row">
          <SearchInput
            value={search}
            onChange={(value) => {
              setSearch(value)
              setPage(1)
            }}
            placeholder="Search drivers"
          />
          <select
            aria-label="Filter driver status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
            className={`${inputClass} sm:w-36`}
          >
            <option value="all">All status</option>
            <option value="AVAILABLE">Available</option>
            <option value="ON_RUN">On run</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
        {query.isLoading ? (
          <LoadingRows />
        ) : query.isError ? (
          <ErrorState onRetry={() => query.refetch()} />
        ) : drivers.length === 0 ? (
          <EmptyState
            title="No drivers found"
            description="Try updating your search or filter."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left">
                <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Driver</th>
                    <th className="px-4 py-3 font-semibold">Contact</th>
                    <th className="px-4 py-3 font-semibold">Availability</th>
                    <th className="px-4 py-3 font-semibold">Max stops</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {drivers.map((driver) => (
                    <tr key={driver.id} className="text-sm">
                      <td className="px-5 py-4">
                        <p className="font-semibold text-slate-800">
                          {driver.name}
                        </p>
                        <p className="mt-0.5 font-mono-ui text-[11px] text-slate-400">
                          DRV-{driver.id}
                        </p>
                      </td>
                      <td className="px-4 py-4 text-slate-600">
                        <p>{driver.phone_number}</p>
                      </td>
                      <td className="px-4 py-4">
                        <Badge
                          tone={
                            driver.status === 'ON_RUN'
                              ? 'blue'
                              : driver.status === 'AVAILABLE'
                                ? 'green'
                                : 'slate'
                          }
                        >
                          {driver.status === 'ON_RUN'
                            ? 'On run'
                            : driver.status === 'AVAILABLE'
                              ? 'Available'
                              : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-4 py-4 font-medium text-slate-700">
                        {driver.max_stops_per_run}
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => setEditing(driver)}
                            aria-label={`Edit ${driver.name}`}
                            className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
                          >
                            <Edit3Icon size={16} />
                          </button>
                          <button
                            onClick={() => setRemoving(driver)}
                            aria-label={`Delete ${driver.name}`}
                            className="rounded-md p-2 text-slate-500 hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2Icon size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={page}
              total={total}
              perPage={5}
              onPageChange={setPage}
            />
          </>
        )}
      </Card>
      {editing !== undefined && (
        <DriverModal driver={editing} onClose={() => setEditing(undefined)} />
      )}
      {removing && (
        <ConfirmDialog
          title="Remove driver?"
          description={`This will remove ${removing.name} from your fleet. Existing run history will remain available.`}
          confirmText="Remove driver"
          loading={deleteMutation.isPending}
          onClose={() => setRemoving(null)}
          onConfirm={() => deleteMutation.mutate(removing.id)}
        />
      )}
    </div>
  )
}

function DriverModal({
  driver,
  onClose,
}: {
  driver: Driver | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<DriverForm>({
    defaultValues: driver
      ? {
          name: driver.name,
          phone_number: driver.phone_number,
          max_stops_per_run: driver.max_stops_per_run,
          active: driver.active,
        }
      : {
          name: '',
          email: '',
          phone_number: '',
          max_stops_per_run: 8,
          active: true,
        },
  })

  const mutation = useMutation({
    mutationFn: (values: DriverForm) => {
      if (driver) {
        return api.updateDriver(driver.id, {
          phone_number: values.phone_number,
          max_stops_per_run: values.max_stops_per_run,
          active: values.active,
        })
      }
      return api.createDriver({
        user_data: {
          email: values.email,
          first_name: values.name.split(' ')[0] || values.name,
          last_name: values.name.split(' ').slice(1).join(' ') || '',
        },
        name: values.name,
        phone_number: values.phone_number,
        max_stops_per_run: values.max_stops_per_run,
        active: values.active,
      } as Partial<Driver>)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drivers'] })
      showToast(driver ? 'Driver updated.' : 'Driver added to fleet.')
      onClose()
    },
  })

  return (
    <Modal title={driver ? 'Edit driver' : 'Add driver'} onClose={onClose}>
      <form
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        className="space-y-4 p-5"
      >
        {!driver && (
          <>
            <Field label="Full name" error={errors.name?.message}>
              <input
                className={inputClass}
                {...register('name', { required: 'Name is required' })}
              />
            </Field>
            <Field label="Work email" error={errors.email?.message}>
              <input
                className={inputClass}
                type="email"
                {...register('email', { required: 'Email is required' })}
              />
            </Field>
          </>
        )}
        <Field label="Phone number">
          <input className={inputClass} {...register('phone_number')} />
        </Field>
        <Field
          label="Max stops per run"
          error={errors.max_stops_per_run?.message}
        >
          <input
            type="number"
            min={1}
            className={inputClass}
            {...register('max_stops_per_run', {
              required: 'Max stops is required',
              min: { value: 1, message: 'Must be at least 1' },
            })}
          />
        </Field>
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <input
            type="checkbox"
            className="h-4 w-4 accent-[#175e58]"
            {...register('active')}
          />{' '}
          Active and available for assignment
        </label>
        {mutation.isError && (
          <p className="text-sm text-red-600">
            Could not save this driver. Please retry.
          </p>
        )}
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            {driver ? 'Save changes' : 'Add driver'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
