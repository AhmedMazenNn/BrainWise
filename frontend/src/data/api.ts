import axios from 'axios'
import type {
  DeliveryRun,
  DeliveryStop,
  Driver,
  Order,
  PaginatedResponse,
  User,
} from '../types/logistics'

const client = axios.create({
  baseURL: '/api',
})

client.interceptors.request.use((config) => {
  const access = localStorage.getItem('access')
  if (access) {
    config.headers.Authorization = `Bearer ${access}`
  }
  return config
})

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (err: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((prom) => {
    if (error || !token) prom.reject(error)
    else prom.resolve(token)
  })
  failedQueue = []
}

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refresh = localStorage.getItem('refresh')
      if (!refresh) {
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
        window.location.href = '/login'
        return Promise.reject(error)
      }
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return client(originalRequest)
        })
      }
      originalRequest._retry = true
      isRefreshing = true
      try {
        const { data } = await axios.post('/api/auth/refresh/', { refresh })
        localStorage.setItem('access', data.access)
        processQueue(null, data.access)
        originalRequest.headers.Authorization = `Bearer ${data.access}`
        return client(originalRequest)
      } catch (err) {
        processQueue(err, null)
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  },
)

export const api = {
  async login(username: string, password: string) {
    const { data } = await client.post<{ access: string; refresh: string }>(
      '/auth/login/',
      { username, password },
    )
    return data
  },

  async getMe() {
    const { data } = await client.get<User>('/auth/me/')
    return data
  },

  async getDrivers(
    params?: Record<string, string | number>,
  ): Promise<PaginatedResponse<Driver>> {
    const { data } = await client.get('/drivers/', { params })
    return data
  },

  async getAvailableDrivers(
    params?: Record<string, string | number>,
  ): Promise<PaginatedResponse<Driver>> {
    const { data } = await client.get('/drivers/available/', { params })
    return data
  },

  async getDriver(id: number) {
    const { data } = await client.get<Driver>(`/drivers/${id}/`)
    return data
  },

  async createDriver(payload: Partial<Driver>) {
    const { data } = await client.post<Driver>('/drivers/', payload)
    return data
  },

  async updateDriver(id: number, payload: Partial<Driver>) {
    const { data } = await client.patch<Driver>(`/drivers/${id}/`, payload)
    return data
  },

  async deleteDriver(id: number) {
    await client.delete(`/drivers/${id}/`)
  },

  async getOrders(
    params?: Record<string, string | number>,
  ): Promise<PaginatedResponse<Order>> {
    const { data } = await client.get('/orders/', { params })
    return data
  },

  async createOrder(payload: Partial<Order>) {
    const { data } = await client.post<Order>('/orders/', payload)
    return data
  },

  async updateOrder(id: number, payload: Partial<Order>) {
    const { data } = await client.patch<Order>(`/orders/${id}/`, payload)
    return data
  },

  async deleteOrder(id: number) {
    await client.delete(`/orders/${id}/`)
  },

  async getRuns(
    params?: Record<string, string | number>,
  ): Promise<PaginatedResponse<DeliveryRun>> {
    const { data } = await client.get('/delivery-runs/', { params })
    return data
  },

  async getRun(id: number) {
    const { data } = await client.get<DeliveryRun>(`/delivery-runs/${id}/`)
    return data
  },

  async createRun(payload: Partial<DeliveryRun>) {
    const { data } = await client.post<DeliveryRun>('/delivery-runs/', payload)
    return data
  },

  async deleteRun(id: number) {
    await client.delete(`/delivery-runs/${id}/`)
  },

  async buildRun(id: number, orderIds: number[]) {
    const { data } = await client.post<DeliveryRun>(
      `/delivery-runs/${id}/build-run/`,
      { order_ids: orderIds },
    )
    return data
  },

  async startRun(id: number) {
    const { data } = await client.post<DeliveryRun>(
      `/delivery-runs/${id}/start-run/`,
    )
    return data
  },

  async completeRun(id: number) {
    const { data } = await client.post<DeliveryRun>(
      `/delivery-runs/${id}/complete-run/`,
    )
    return data
  },

  async bankCash(id: number, cashBankedLocation: string) {
    const { data } = await client.post<DeliveryRun>(
      `/delivery-runs/${id}/bank-cash/`,
      { cash_banked_location: cashBankedLocation },
    )
    return data
  },

  async getStops(
    params?: Record<string, string | number>,
  ): Promise<PaginatedResponse<DeliveryStop>> {
    const { data } = await client.get('/delivery-stops/', { params })
    return data
  },

  async markDelivered(id: number) {
    const { data } = await client.post<DeliveryStop>(
      `/delivery-stops/${id}/mark-delivered/`,
    )
    return data
  },

  async markFailed(id: number, failedReason: string) {
    const { data } = await client.post<DeliveryStop>(
      `/delivery-stops/${id}/mark-failed/`,
      { failed_reason: failedReason },
    )
    return data
  },
}
