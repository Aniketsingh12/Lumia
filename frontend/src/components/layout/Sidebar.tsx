import { NavLink } from 'react-router-dom'
import {
  Sparkles, LayoutDashboard, MessageSquare, BarChart3, BookOpen, Settings, LogOut, X,
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { cn } from '../../lib/utils'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/conversations', icon: MessageSquare, label: 'Conversations' },
  { to: '/knowledge', icon: BookOpen, label: 'Knowledge Base' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

interface SidebarProps {
  /** Mobile drawer state. On lg+ the sidebar is always visible. */
  open: boolean
  onClose: () => void
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout } = useAuth()

  return (
    <>
      {/* Mobile scrim — closes the drawer on tap. Hidden on lg+. */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden transition-opacity duration-300',
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        className={cn(
          'fixed left-0 top-0 z-50 h-screen w-[17rem] flex flex-col',
          'bg-hero-bg border-r border-border text-muted-foreground',
          'shadow-depth-xl transition-transform duration-300 ease-out',
          // Slides in on mobile; permanently docked from lg up.
          open ? 'translate-x-0' : '-translate-x-full',
          'lg:translate-x-0'
        )}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-border">
          <div className="icon-tile w-10 h-10 flex-shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <span className="block text-lg font-bold tracking-tight text-foreground leading-none">
              Lumio
            </span>
            <span className="block text-[11px] text-ink-400 mt-1">AI Chat Platform</span>
          </div>
          {/* Close button only exists on mobile */}
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 -mr-1 text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium',
                  'transition-all duration-200',
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-glow'
                    : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                )
              }
            >
              {({ isActive }) => (
                <>
                  {/* Active indicator rail */}
                  <span
                    className={cn(
                      'absolute left-0 top-1/2 -translate-y-1/2 w-1 rounded-r-full bg-accent-400 transition-all duration-200',
                      isActive ? 'h-6 opacity-100' : 'h-0 opacity-0'
                    )}
                  />
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  <span className="truncate">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-border p-3">
          <div className="flex items-center gap-3 rounded-xl bg-secondary/60 border border-border p-2.5">
            <div className="w-9 h-9 flex-shrink-0 rounded-full bg-gradient-to-br from-primary-400 to-accent-500 flex items-center justify-center text-primary-foreground text-sm font-bold">
              {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-foreground truncate">{user?.full_name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
            <button
              onClick={logout}
              className="p-1.5 text-ink-400 hover:text-red-400 transition-colors flex-shrink-0"
              title="Log out"
              aria-label="Log out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
