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
import type { Order, OrderStatus, OrderPriority } from '../types/logistics'
import { useToast } from '../contexts/ToastContext'
import axios from 'axios'

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

const toneForStatus: Record<OrderStatus, 'green' | 'amber' | 'blue' | 'red' | 'slate'> = {
  OPEN: 'amber',
  ASSIGNED: 'blue',
  EN_ROUTE: 'blue',
  DELIVERED: 'green',
  FAILED: 'red',
  CASH_BANKED: 'green',
}

const toneForPriority: Record<OrderPriority, 'slate' | 'amber' | 'red'> = {
  LOW: 'slate',
  MEDIUM: 'amber',
  HIGH: 'red',
}

type OrderForm = {
  customer_name: string
  customer_phone: string
  address: string
  cash_amount: number
  priority: OrderPriority
}

export function OrdersPage() {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [priority, setPriority] = useState('all')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Order | null | undefined>(undefined)
  const [removing, setRemoving] = useState<Order | null>(null)

  const query = useQuery({
    queryKey: ['orders', { search, status, priority, page }],
    queryFn: () => {
      const params: Record<string, string | number> = { page, page_size: 5 }
      if (search) params.search = search
      if (status !== 'all') params.status = status
      if (priority !== 'all') params.priority = priority
      return api.getOrders(params)
    },
  })

  const orders = query.data?.results ?? []
  const total = query.data?.count ?? 0

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteOrder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      showToast('Order deleted.')
      setRemoving(null)
    },
    onError: (err) => {
      showToast(getApiError(err), 'error')
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[#175e58]">Order management</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">Orders</h1>
          <p className="mt-1 text-sm text-slate-500">
            Create, review, and route customer deliveries.
          </p>
        </div>
        <Button onClick={() => setEditing(null)}>
          <PlusIcon size={16} />
          Create order
        </Button>
      </div>
      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 lg:flex-row">
          <SearchInput
            value={search}
            onChange={(value) => {
              setSearch(value)
              setPage(1)
            }}
            placeholder="Search order or customer"
          />
          <select
            aria-label="Filter order status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
            className={`${inputClass} lg:w-36`}
          >
            <option value="all">All status</option>
            {['OPEN', 'ASSIGNED', 'EN_ROUTE', 'DELIVERED', 'FAILED', 'CASH_BANKED'].map((value) => (
              <option key={value} value={value}>{value.replace('_', ' ')}</option>
            ))}
          </select>
          <select
            aria-label="Filter priority"
            value={priority}
            onChange={(event) => {
              setPriority(event.target.value)
              setPage(1)
            }}
            className={`${inputClass} lg:w-36`}
          >
            <option value="all">All priority</option>
            {['HIGH', 'MEDIUM', 'LOW'].map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
        </div>
        {query.isLoading ? (
          <LoadingRows />
        ) : query.isError ? (
          <ErrorState onRetry={() => query.refetch()} />
        ) : orders.length === 0 ? (
          <EmptyState
            title="No orders found"
            description="Try updating your filters or create a new order."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[850px] text-left">
                <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-5 py-3">Order</th>
                    <th className="px-4 py-3">Customer</th>
                    <th className="px-4 py-3">Cash due</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Priority</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {orders.map((order) => (
                    <tr className="text-sm" key={order.id}>
                      <td className="px-5 py-4">
                        <p className="font-mono-ui text-xs font-semibold text-slate-700">
                          ORD-{order.id}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          {new Date(order.created_at).toLocaleDateString()}
                        </p>
                      </td>
                      <td className="px-4 py-4">
                        <p className="font-semibold text-slate-800">
                          {order.customer_name}
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {order.address}
                        </p>
                      </td>
                      <td className="px-4 py-4 font-semibold text-slate-700">
                        ${Number(order.cash_amount).toLocaleString()}
                      </td>
                      <td className="px-4 py-4">
                        <Badge tone={toneForStatus[order.status]}>
                          {order.status.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="px-4 py-4">
                        <Badge tone={toneForPriority[order.priority]}>
                          {order.priority}
                        </Badge>
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => setEditing(order)}
                            aria-label={`Edit ORD-${order.id}`}
                            className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
                          >
                            <Edit3Icon size={16} />
                          </button>
                          {order.status === 'OPEN' && (
                            <button
                              onClick={() => setRemoving(order)}
                              aria-label={`Delete ORD-${order.id}`}
                              className="rounded-md p-2 text-slate-500 hover:bg-red-50 hover:text-red-600"
                            >
                              <Trash2Icon size={16} />
                            </button>
                          )}
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
        <OrderModal order={editing} onClose={() => setEditing(undefined)} />
      )}
      {removing && (
        <ConfirmDialog
          title="Delete open order?"
          description={`This will permanently delete ORD-${removing.id}. Assigned or completed orders cannot be deleted.`}
          confirmText="Delete order"
          onClose={() => setRemoving(null)}
          onConfirm={() => deleteMutation.mutate(removing.id)}
          loading={deleteMutation.isPending}
        />
      )}
    </div>
  )
}

function OrderModal({
  order,
  onClose,
}: {
  order: Order | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<OrderForm>({
    defaultValues: order
      ? {
          customer_name: order.customer_name,
          customer_phone: order.customer_phone,
          address: order.address,
          cash_amount: Number(order.cash_amount),
          priority: order.priority,
        }
      : {
          customer_name: '',
          customer_phone: '',
          address: '',
          cash_amount: 0,
          priority: 'MEDIUM',
        },
  })

  const mutation = useMutation({
    mutationFn: (values: OrderForm) => {
      if (order) {
        return api.updateOrder(order.id, {
          customer_name: values.customer_name,
          customer_phone: values.customer_phone,
          address: values.address,
          cash_amount: String(values.cash_amount),
          priority: values.priority,
        })
      }
      return api.createOrder({
        customer_name: values.customer_name,
        customer_phone: values.customer_phone,
        address: values.address,
        cash_amount: String(values.cash_amount),
        priority: values.priority,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      showToast(order ? 'Order updated.' : 'Order created.')
      onClose()
    },
  })

  return (
    <Modal title={order ? 'Edit order' : 'Create order'} onClose={onClose}>
      <form
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        className="space-y-4 p-5"
      >
        <Field label="Customer name" error={errors.customer_name?.message}>
          <input
            className={inputClass}
            {...register('customer_name', {
              required: 'Customer name is required',
            })}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Phone" error={errors.customer_phone?.message}>
            <input
              className={inputClass}
              placeholder="+201234567890"
              {...register('customer_phone', {
                pattern: {
                  value: /^\+?[\d\s\-()]{7,20}$/,
                  message: 'Enter a valid phone number (e.g. +201234567890)',
                },
              })}
            />
          </Field>
          <Field label="Cash due" error={errors.cash_amount?.message}>
            <input
              type="number"
              min="0"
              step="0.01"
              className={inputClass}
              {...register('cash_amount', {
                required: 'Cash amount is required',
                min: { value: 0, message: 'Enter a valid amount' },
              })}
            />
          </Field>
        </div>
        <Field label="Delivery address" error={errors.address?.message}>
          <input
            className={inputClass}
            {...register('address', {
              required: 'Address is required',
            })}
          />
        </Field>
        <Field label="Priority">
          <select className={inputClass} {...register('priority')}>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </Field>
        {mutation.isError && (
          <p className="text-sm text-red-600">
            {getApiError(mutation.error)}
          </p>
        )}
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            {order ? 'Save changes' : 'Create order'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
