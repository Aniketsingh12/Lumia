import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
})

// Attach auth token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses — clear auth state and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Import lazily to avoid circular dependency
      import('../stores/authStore').then(({ useAuthStore }) => {
        useAuthStore.getState().logout()
      })
      window.location.replace('/login')
    }
    return Promise.reject(error)
  }
)

/**
 * Extract a human-readable error message from an Axios error.
 * FastAPI returns `{ detail: string | ValidationError[] }`.
 */
export function getErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (!error) return fallback
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const axiosError = error as any
  const detail = axiosError?.response?.data?.detail
  if (!detail) return axiosError?.message || fallback
  if (typeof detail === 'string') return detail
  // Pydantic v2 validation error array: [{loc, msg, type}]
  if (Array.isArray(detail)) {
    return detail.map((e: { msg: string }) => e.msg).join(', ')
  }
  return fallback
}

export default api
