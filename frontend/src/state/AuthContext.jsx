import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import api from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('gemelos-token')
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get('/api/auth/me')
      .then((response) => setUser(response.data))
      .catch(() => {
        localStorage.removeItem('gemelos-token')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      async login(payload) {
        const response = await api.post('/api/auth/login', payload)
        localStorage.setItem('gemelos-token', response.data.access_token)
        setUser(response.data.user)
        return response.data.user
      },
      async register(payload) {
        const response = await api.post('/api/auth/register', payload)
        localStorage.setItem('gemelos-token', response.data.access_token)
        setUser(response.data.user)
        return response.data.user
      },
      logout() {
        localStorage.removeItem('gemelos-token')
        setUser(null)
      },
    }),
    [loading, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
