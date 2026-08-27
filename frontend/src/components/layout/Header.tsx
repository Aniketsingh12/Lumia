import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Search, Menu, Bot as BotIcon, X } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { useBotStore } from '../../stores/botStore'
import { cn } from '../../lib/utils'

interface HeaderProps {
  onMenuClick: () => void
}

export default function Header({ onMenuClick }: HeaderProps) {
  const user = useAuthStore((s) => s.user)
  const { bots, fetchBots } = useBotStore()
  const navigate = useNavigate()

  const [query, setQuery] = useState('')
  const [openResults, setOpenResults] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)

  // Bots power the search index; fetch once if the store is still empty.
  useEffect(() => {
    if (bots.length === 0) fetchBots().catch(() => {})
  }, [bots.length, fetchBots])

  // Close the results dropdown when clicking anywhere outside it.
  useEffect(() => {
    const onClickAway = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setOpenResults(false)
      }
    }
    document.addEventListener('mousedown', onClickAway)
    return () => document.removeEventListener('mousedown', onClickAway)
  }, [])

  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return []
    return bots.filter((b) => b.name.toLowerCase().includes(q)).slice(0, 6)
  }, [query, bots])

  // "Needs attention" = bots that are live. Cheap, honest signal rather than a
  // permanently-red dot that means nothing.
  const activeCount = bots.filter((b) => b.is_active).length

  const goToBot = (id: string) => {
    setQuery('')
    setOpenResults(false)
    navigate(`/bots/${id}`)
  }

  return (
    <header className="sticky top-0 z-30 h-16 flex items-center gap-3 px-4 sm:px-6 bg-background/80 backdrop-blur-xl border-b border-border">
      {/* Hamburger — mobile only */}
      <button
        onClick={onMenuClick}
        className="lg:hidden btn-ghost !px-2"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Search */}
      <div ref={searchRef} className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-400 pointer-events-none" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpenResults(true)
          }}
          onFocus={() => setOpenResults(true)}
          placeholder="Search bots…"
          className="input pl-9 pr-8"
          aria-label="Search bots"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('')
              setOpenResults(false)
            }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-ink-400 hover:text-ink-600"
            aria-label="Clear search"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        {/* Results dropdown */}
        {openResults && query.trim() && (
          <div className="absolute top-full left-0 right-0 mt-2 card p-1.5 max-h-72 overflow-y-auto">
            {results.length === 0 ? (
              <p className="px-3 py-2.5 text-sm text-ink-500">
                No bots match "{query.trim()}"
              </p>
            ) : (
              results.map((bot) => (
                <button
                  key={bot.id}
                  onClick={() => goToBot(bot.id)}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-left hover:bg-primary-50 transition-colors"
                >
                  <div className="icon-tile-soft w-8 h-8 flex-shrink-0">
                    <BotIcon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-ink-900 truncate">{bot.name}</p>
                    <p className="text-xs text-ink-500 capitalize truncate">
                      {bot.is_active ? 'Active' : 'Draft'} · {bot.tone}
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2 sm:gap-3 ml-auto">
        <button
          onClick={() => navigate('/conversations')}
          className="relative btn-ghost !px-2"
          aria-label={`Conversations${activeCount ? `, ${activeCount} bots live` : ''}`}
          title="Conversations"
        >
          <Bell className="w-5 h-5" />
          {activeCount > 0 && (
            <span className="absolute top-1 right-1 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 text-[10px] font-bold text-primary-foreground flex items-center justify-center shadow-glow">
              {activeCount}
            </span>
          )}
        </button>

        <div
          className={cn(
            'w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0',
            'bg-gradient-to-br from-primary-500 to-accent-500 text-primary-foreground text-sm font-bold',
            'shadow-glow'
          )}
          title={user?.full_name || 'User'}
        >
          {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
        </div>
      </div>
    </header>
  )
}
