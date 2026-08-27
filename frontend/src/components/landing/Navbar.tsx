import { Link } from 'react-router-dom'
import { Button } from '../ui/button'
import { useAuthStore } from '../../stores/authStore'

/**
 * Fixed, transparent navbar that floats over the Spline hero.
 *
 * Section anchors match the ids rendered by pages/Landing.tsx.
 * Below `md` the links and CTA hide entirely (no hamburger) — the hero's own
 * buttons carry the primary actions on small screens.
 */
const navLinks = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Channels', href: '#channels' },
  { label: 'Open Source', href: '#open-source' },
]

export default function Navbar() {
  // Returning visitors with a live session get "Dashboard" instead of "Get Started".
  const token = useAuthStore((s) => s.token)

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 lg:px-16 py-5">
      <Link to="/" className="text-foreground text-xl font-semibold tracking-tight">
        LUMIO
      </Link>

      <div className="hidden md:flex items-center gap-8">
        {navLinks.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors uppercase tracking-widest"
          >
            {link.label}
          </a>
        ))}
      </div>

      <Link to={token ? '/dashboard' : '/login'} className="hidden md:inline-flex">
        <Button variant="navCta" size="lg" className="rounded-lg uppercase text-xs tracking-widest px-6">
          {token ? 'Dashboard' : 'Get Started'}
        </Button>
      </Link>
    </nav>
  )
}
