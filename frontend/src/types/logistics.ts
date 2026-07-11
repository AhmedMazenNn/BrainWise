export type Role = 'MANAGER' | 'DISPATCHER' | 'DRIVER'

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  role: Role
  date_joined: string
}

export type DriverStatus = 'AVAILABLE' | 'ON_RUN' | 'INACTIVE'

export interface Driver {
  id: number
  user: number
  name: string
  phone_number: string
  active: boolean
  max_stops_per_run: number
  status: DriverStatus
  created_at: string
  updated_at: string
}

export type OrderPriority = 'HIGH' | 'MEDIUM' | 'LOW'

export type OrderStatus =
  | 'OPEN'
  | 'ASSIGNED'
  | 'EN_ROUTE'
  | 'DELIVERED'
  | 'FAILED'
  | 'CASH_BANKED'

export interface Order {
  id: number
  customer_name: string
  customer_phone: string
  address: string
  cash_amount: string
  priority: OrderPriority
  status: OrderStatus
  assigned_driver: number | null
  created_at: string
  delivered_at: string | null
  updated_at: string
}

export type RunStatus =
  | 'DRAFT'
  | 'ASSIGNED'
  | 'EN_ROUTE'
  | 'COMPLETED'
  | 'CASH_BANKED'
  | 'CANCELLED'

export interface DeliveryRun {
  id: number
  driver: number
  driver_name: string
  status: RunStatus
  total_cash_collected: string
  started_at: string | null
  completed_at: string | null
  cash_banked_at: string | null
  cash_banked_location: string
  created_at: string
  updated_at: string
  stops_count?: number
}

export type StopStatus = 'ASSIGNED' | 'EN_ROUTE' | 'DELIVERED' | 'FAILED'

export interface DeliveryStop {
  id: number
  delivery_run: number
  order: number
  stop_sequence: number
  customer_name: string
  address: string
  cash_amount: string
  status: StopStatus
  delivered_at: string | null
  failed_reason: string
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
