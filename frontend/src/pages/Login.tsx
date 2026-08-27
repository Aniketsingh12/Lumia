import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, Loader2, Eye, EyeOff, PlayCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { getErrorMessage } from '../lib/api'
import toast from 'react-hot-toast'

// Optional demo account, inlined at build time (Vite only exposes VITE_* vars).
// Set VITE_DEMO_EMAIL to surface a one-click "try it" button — the deployed
// portfolio demo does, so a visitor never has to guess credentials. Leave it
// unset on a real client deployment and the whole block disappears.
const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL || ''
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || ''

export default function Login() {
  const { login, loading } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const signIn = async (emailArg: string, passwordArg: string) => {
    try {
      await login(emailArg, passwordArg)
      toast.success('Welcome back!')
    } catch (err) {
      toast.error(getErrorMessage(err, 'Login failed. Please try again.'))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await signIn(email, password)
  }

  // Fill the form as well as submitting it, so the visitor can see which
  // account they were signed in as rather than being teleported to the
  // dashboard with no explanation.
  const handleDemoLogin = async () => {
    setEmail(DEMO_EMAIL)
    setPassword(DEMO_PASSWORD)
    await signIn(DEMO_EMAIL, DEMO_PASSWORD)
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative">
      <div className="app-mesh" />
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2">
            <span className="icon-tile w-11 h-11"><Sparkles className="w-6 h-6" /></span>
            <span className="text-2xl font-bold text-ink-900">Lumio</span>
          </Link>
          <h1 className="mt-6 text-2xl font-bold text-gray-900">Welcome back</h1>
          <p className="mt-2 text-gray-600">Sign in to your account</p>
        </div>

        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@company.com"
                required
              />
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pr-10"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-gray-600"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Sign In
            </button>
          </form>

          {DEMO_EMAIL && (
            <>
              <div className="relative my-5">
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className="w-full border-t border-ink-200" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-card px-3 text-xs uppercase tracking-wide text-ink-400">
                    or
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={loading}
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                <PlayCircle className="w-4 h-4" />
                Explore the live demo
              </button>

              <p className="mt-3 text-center text-xs text-ink-500">
                Signs you in as{' '}
                <code className="font-mono text-ink-600">{DEMO_EMAIL}</code>. It's a shared
                sandbox — anything you create here is visible to other visitors and resets
                periodically.
              </p>
            </>
          )}
        </div>

        <p className="text-center mt-4 text-sm text-gray-600">
          Don't have an account?{' '}
          <Link to="/signup" className="text-primary-600 font-medium hover:text-primary-700">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
