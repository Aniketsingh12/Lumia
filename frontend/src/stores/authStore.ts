import { create } from 'zustand'
import api from '../lib/api'

interface User {
  id: string
  email: string
  full_name: string
  org_id: string
  role: string
  avatar_url?: string
}

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, fullName: string, orgName?: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  loading: false,

  login: async (email, password) => {
    set({ loading: true })
    try {
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('token', data.access_token)
      set({ token: data.access_token, user: data.user, loading: false })
    } catch (error) {
      set({ loading: false })
      throw error
    }
  },

  signup: async (email, password, fullName, orgName) => {
    set({ loading: true })
    try {
      const { data } = await api.post('/auth/signup', {
        email,
        password,
        full_name: fullName,
        org_name: orgName,
      })
      localStorage.setItem('token', data.access_token)
      set({ token: data.access_token, user: data.user, loading: false })
    } catch (error) {
      set({ loading: false })
      throw error
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null })
  },

  loadUser: async () => {
    try {
      const { data } = await api.get('/auth/me')
      set({ user: data })
    } catch {
      localStorage.removeItem('token')
      set({ user: null, token: null })
    }
  },
}))
