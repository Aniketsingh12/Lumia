import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export function useAuth() {
  const { user, token, loading, login, signup, logout, loadUser } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (token && !user) {
      loadUser()
    }
  }, [token, user, loadUser])

  const handleLogin = async (email: string, password: string) => {
    await login(email, password)
    navigate('/dashboard')
  }

  const handleSignup = async (email: string, password: string, fullName: string, orgName?: string) => {
    await signup(email, password, fullName, orgName)
    navigate('/dashboard')
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return { user, token, loading, login: handleLogin, signup: handleSignup, logout: handleLogout }
}
