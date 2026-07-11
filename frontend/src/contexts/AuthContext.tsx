import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../data/api'
import type { User } from '../types/logistics'

interface AuthState {
  user: User | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const access = localStorage.getItem('access')
    if (!access) {
      setIsLoading(false)
      return
    }
    api
      .getMe()
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const tokens = await api.login(username, password)
    localStorage.setItem('access', tokens.access)
    localStorage.setItem('refresh', tokens.refresh)
    const u = await api.getMe()
    setUser(u)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
