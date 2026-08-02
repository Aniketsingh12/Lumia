import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Bot, MessageSquare, Zap, Users, Loader2 } from 'lucide-react'
import { useBots } from '../hooks/useBots'
import { cn, getStatusColor, getChannelIcon } from '../lib/utils'
import { BOT_GENRES, getGenre } from '../lib/genres'
import { getErrorMessage } from '../lib/api'
import toast from 'react-hot-toast'
import Badge from '../components/common/Badge'
import EmptyState from '../components/common/EmptyState'
import Modal from '../components/common/Modal'

export default function Dashboard() {
  const { bots, loading, createBot } = useBots()
  const navigate = useNavigate()
  const [showCreate, setShowCreate] = useState(false)
  const [newBotName, setNewBotName] = useState('')
  const [newBotType, setNewBotType] = useState('support')
  const [newBotPersona, setNewBotPersona] = useState('')
  const [creating, setCreating] = useState(false)

  const selectedGenre = getGenre(newBotType)

  const handleCreate = async () => {
    if (!newBotName.trim()) return
    if (selectedGenre.usesPersona && !newBotPersona.trim()) {
      toast.error('Describe your character first')
      return
    }
    setCreating(true)
    try {
      const bot = await createBot({
        name: newBotName,
        bot_type: newBotType,
        persona: newBotPersona.trim() || null,
      })
      toast.success('Bot created!')
      setShowCreate(false)
      setNewBotName('')
      setNewBotType('support')
      setNewBotPersona('')
      navigate(`/bots/${bot.id}`)
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to create bot'))
    }
    setCreating(false)
  }

  const totalMessages = bots.reduce((sum, b) => sum + (b.message_count || 0), 0)
  const activeBots = bots.filter((b) => b.is_active).length

  return (
    <div>
      {/* Page title */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink-900">
          Welcome back
        </h1>
        <p className="text-ink-500 mt-1 text-sm sm:text-base">
          Here's what's happening across your bots.
        </p>
      </div>

      {/* Stats — 2-up on phones, 4-up from md */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
        {[
          { label: 'Total Bots', value: bots.length, icon: Bot, tint: 'from-primary-500 to-primary-700' },
          { label: 'Active Bots', value: activeBots, icon: Zap, tint: 'from-emerald-500 to-teal-600' },
          { label: 'Total Messages', value: totalMessages, icon: MessageSquare, tint: 'from-sky-500 to-blue-600' },
          { label: 'Team Members', value: 1, icon: Users, tint: 'from-fuchsia-500 to-purple-600' },
        ].map((stat) => (
          <div key={stat.label} className="card-3d p-4 sm:p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs sm:text-sm text-ink-500 truncate">{stat.label}</p>
                <p className="text-2xl sm:text-3xl font-bold text-ink-900 mt-1 tabular-nums">
                  {stat.value}
                </p>
              </div>
              <div
                className={cn(
                  'w-10 h-10 sm:w-11 sm:h-11 flex-shrink-0 rounded-xl flex items-center justify-center',
                  'bg-gradient-to-br text-white shadow-depth',
                  stat.tint
                )}
              >
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Bot List Header */}
      <div className="flex items-center justify-between gap-3 mb-5">
        <h2 className="text-lg sm:text-xl font-bold text-ink-900">My Bots</h2>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Create New Bot</span>
          <span className="sm:hidden">New</span>
        </button>
      </div>

      {/* Bot List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      ) : bots.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No bots yet"
          description="Create your first AI chatbot to get started"
          action={{ label: 'Create Bot', onClick: () => setShowCreate(true) }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {bots.map((bot) => (
            <div
              key={bot.id}
              onClick={() => navigate(`/bots/${bot.id}`)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  navigate(`/bots/${bot.id}`)
                }
              }}
              className="card-3d p-5 cursor-pointer group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400 focus-visible:ring-offset-2"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="icon-tile w-11 h-11 flex-shrink-0 transition-transform duration-300 group-hover:scale-110">
                    {(() => {
                      const GenreIcon = getGenre(bot.bot_type).icon
                      return <GenreIcon className="w-5 h-5" />
                    })()}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-bold text-ink-900 truncate">{bot.name}</h3>
                    <p className="text-sm text-ink-500 truncate">
                      {getGenre(bot.bot_type).label} · <span className="capitalize">{bot.tone}</span>
                    </p>
                  </div>
                </div>
                <Badge status={bot.is_active ? 'active' : 'draft'}>
                  {bot.is_active ? 'Active' : 'Draft'}
                </Badge>
              </div>
              <div className="flex items-center gap-4 text-sm text-ink-500">
                <span>{bot.message_count || 0} messages</span>
                <span>{bot.doc_count || 0} docs</span>
              </div>
              <div className="flex items-center gap-1 mt-3">
                {Object.entries(bot.channels || {})
                  // Channel values are objects now, so check the flag rather
                  // than truthiness — {connected:false} is still truthy.
                  .filter(([, v]) => v?.connected)
                  .map(([channel]) => (
                    <span key={channel} className="text-lg" title={channel}>
                      {getChannelIcon(channel)}
                    </span>
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Bot Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create New Bot">
        <div className="space-y-4">
          <div>
            <label className="label">Bot Name</label>
            <input
              type="text"
              value={newBotName}
              onChange={(e) => setNewBotName(e.target.value)}
              className="input"
              placeholder="e.g., Support Bot"
              autoFocus
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
          </div>

          {/* Genre picker */}
          <div>
            <label className="label">What kind of bot?</label>
            <div className="grid grid-cols-2 gap-2">
              {BOT_GENRES.map((genre) => (
                <button
                  key={genre.id}
                  type="button"
                  onClick={() => setNewBotType(genre.id)}
                  className={cn(
                    'text-left p-3 rounded-lg border transition-colors',
                    newBotType === genre.id
                      ? 'bg-primary-50 border-primary-300'
                      : 'bg-white border-gray-200 hover:border-gray-300'
                  )}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <genre.icon
                      className={cn(
                        'w-4 h-4',
                        newBotType === genre.id ? 'text-primary-600' : 'text-gray-400'
                      )}
                    />
                    <span
                      className={cn(
                        'text-sm font-medium',
                        newBotType === genre.id ? 'text-primary-700' : 'text-gray-700'
                      )}
                    >
                      {genre.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 leading-snug">{genre.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Persona — required for character bots */}
          {selectedGenre.usesPersona && (
            <div>
              <label className="label">Describe your character</label>
              <textarea
                value={newBotPersona}
                onChange={(e) => setNewBotPersona(e.target.value)}
                className="input min-h-[80px] resize-y"
                rows={3}
                placeholder={selectedGenre.personaPlaceholder}
              />
              <p className="text-xs text-gray-400 mt-1">
                The bot will fully become this character in every chat
              </p>
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button onClick={() => setShowCreate(false)} className="btn-secondary">
              Cancel
            </button>
            <button onClick={handleCreate} disabled={creating || !newBotName.trim()} className="btn-primary flex items-center gap-2">
              {creating && <Loader2 className="w-4 h-4 animate-spin" />}
              Create Bot
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
