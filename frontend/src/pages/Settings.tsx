import { useState, useEffect, useCallback } from 'react'
import {
  Building, Users, Webhook, Key, Plus, Loader2, Copy, Check, ShieldAlert,
} from 'lucide-react'
import api, { getErrorMessage } from '../lib/api'
import toast from 'react-hot-toast'
import { cn } from '../lib/utils'
import Modal from '../components/common/Modal'

const settingsTabs = [
  { id: 'org', label: 'Organization', icon: Building },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'webhooks', label: 'Webhooks', icon: Webhook },
  { id: 'api-keys', label: 'API Keys', icon: Key },
]

interface TeamMember {
  id: string
  email: string
  full_name?: string
  role?: string
}

interface WebhookRow {
  id: string
  url: string
  events?: string[]
}

interface ApiKeyRow {
  id: string
  name: string
  prefix: string
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState('org')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [orgName, setOrgName] = useState('')
  const [team, setTeam] = useState<TeamMember[]>([])
  const [webhooks, setWebhooks] = useState<WebhookRow[]>([])
  const [apiKeys, setApiKeys] = useState<ApiKeyRow[]>([])

  // Creation modals
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteName, setInviteName] = useState('')
  const [inviteRole, setInviteRole] = useState('agent')

  const [hookOpen, setHookOpen] = useState(false)
  const [hookUrl, setHookUrl] = useState('')

  const [keyOpen, setKeyOpen] = useState(false)
  const [keyName, setKeyName] = useState('')
  // The full API key is returned exactly once on creation.
  const [newKey, setNewKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    try {
      const [org, t, w, k] = await Promise.all([
        api.get('/settings/org'),
        api.get('/settings/team'),
        api.get('/settings/webhooks'),
        api.get('/settings/api-keys'),
      ])
      setOrgName(org.data?.name || '')
      setTeam(t.data || [])
      setWebhooks(w.data || [])
      setApiKeys(k.data || [])
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to load settings'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const saveOrg = async () => {
    setSaving(true)
    try {
      await api.put('/settings/org', { name: orgName })
      toast.success('Organization updated')
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update'))
    }
    setSaving(false)
  }

  const inviteMember = async () => {
    if (!inviteEmail.trim()) return
    setSaving(true)
    try {
      await api.post('/settings/team', {
        email: inviteEmail.trim(),
        full_name: inviteName.trim() || undefined,
        role: inviteRole,
      })
      toast.success('Team member invited')
      setInviteOpen(false)
      setInviteEmail('')
      setInviteName('')
      await load()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to invite'))
    }
    setSaving(false)
  }

  const createWebhook = async () => {
    if (!hookUrl.trim()) return
    setSaving(true)
    try {
      await api.post('/settings/webhooks', { url: hookUrl.trim() })
      toast.success('Webhook created')
      setHookOpen(false)
      setHookUrl('')
      await load()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to create webhook'))
    }
    setSaving(false)
  }

  const createApiKey = async () => {
    setSaving(true)
    try {
      const { data } = await api.post('/settings/api-keys', {
        name: keyName.trim() || 'Default',
      })
      setNewKey(data.key)
      setKeyName('')
      await load()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to create API key'))
    }
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink-900 mb-6">
        Settings
      </h1>

      {/* Stacks on mobile, side-by-side from md */}
      <div className="flex flex-col md:flex-row gap-4 md:gap-6">
        {/* Tabs — horizontal scroller on mobile, vertical rail on desktop */}
        <div className="md:w-52 flex-shrink-0">
          <div className="flex md:flex-col gap-1 overflow-x-auto pb-1 md:pb-0">
            {settingsTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-semibold',
                  'whitespace-nowrap flex-shrink-0 md:w-full transition-all duration-200',
                  activeTab === tab.id
                    ? 'bg-gradient-to-br from-primary-500 to-primary-700 text-white shadow-glow'
                    : 'text-ink-600 hover:bg-white/70 hover:text-ink-900'
                )}
              >
                <tab.icon className="w-4 h-4 flex-shrink-0" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 card p-5 sm:p-6 min-w-0">
          {activeTab === 'org' && (
            <div>
              <h2 className="text-lg font-bold text-ink-900 mb-4">Organization</h2>
              <div className="max-w-md space-y-4">
                <div>
                  <label className="label">Organization name</label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="input"
                    placeholder="Acme Inc."
                  />
                </div>
                <button onClick={saveOrg} disabled={saving} className="btn-primary">
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  Save changes
                </button>
              </div>
            </div>
          )}

          {activeTab === 'team' && (
            <div>
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-lg font-bold text-ink-900">Team members</h2>
                <button onClick={() => setInviteOpen(true)} className="btn-primary">
                  <Plus className="w-4 h-4" />
                  <span className="hidden sm:inline">Invite</span>
                </button>
              </div>
              {team.length === 0 ? (
                <p className="text-ink-500 text-sm">No team members yet.</p>
              ) : (
                <div className="divide-y divide-ink-100">
                  {team.map((member) => (
                    <div
                      key={member.id}
                      className="flex items-center justify-between gap-3 py-3"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-9 h-9 flex-shrink-0 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 text-white flex items-center justify-center text-sm font-bold">
                          {(member.full_name || member.email).charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-ink-900 truncate">
                            {member.full_name || member.email}
                          </p>
                          <p className="text-sm text-ink-500 truncate">{member.email}</p>
                        </div>
                      </div>
                      <span className="text-xs font-semibold text-primary-700 bg-primary-50 border border-primary-200/60 px-2.5 py-1 rounded-full capitalize flex-shrink-0">
                        {member.role || 'agent'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'webhooks' && (
            <div>
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-lg font-bold text-ink-900">Webhooks</h2>
                <button onClick={() => setHookOpen(true)} className="btn-primary">
                  <Plus className="w-4 h-4" />
                  <span className="hidden sm:inline">Add webhook</span>
                </button>
              </div>
              <p className="text-sm text-ink-500 mb-4">
                We'll POST to these URLs when messages arrive or conversations escalate.
              </p>
              {webhooks.length === 0 ? (
                <p className="text-ink-500 text-sm">No webhooks configured.</p>
              ) : (
                <div className="divide-y divide-ink-100">
                  {webhooks.map((wh) => (
                    <div key={wh.id} className="py-3 min-w-0">
                      <p className="font-mono text-sm text-ink-800 break-all">{wh.url}</p>
                      <p className="text-xs text-ink-500 mt-1">
                        Events: {wh.events?.join(', ') || '—'}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'api-keys' && (
            <div>
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-lg font-bold text-ink-900">API keys</h2>
                <button onClick={() => setKeyOpen(true)} className="btn-primary">
                  <Plus className="w-4 h-4" />
                  <span className="hidden sm:inline">Create key</span>
                </button>
              </div>
              {apiKeys.length === 0 ? (
                <p className="text-ink-500 text-sm">No API keys created.</p>
              ) : (
                <div className="divide-y divide-ink-100">
                  {apiKeys.map((key) => (
                    <div
                      key={key.id}
                      className="flex items-center justify-between gap-3 py-3"
                    >
                      <div className="min-w-0">
                        <p className="font-semibold text-ink-900 truncate">{key.name}</p>
                        <p className="font-mono text-sm text-ink-500 truncate">
                          {key.prefix}…
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Invite member */}
      <Modal open={inviteOpen} onClose={() => setInviteOpen(false)} title="Invite team member">
        <div className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="input"
              placeholder="teammate@company.com"
              autoFocus
            />
          </div>
          <div>
            <label className="label">Full name (optional)</label>
            <input
              type="text"
              value={inviteName}
              onChange={(e) => setInviteName(e.target.value)}
              className="input"
              placeholder="Jane Smith"
            />
          </div>
          <div>
            <label className="label">Role</label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="input"
            >
              <option value="agent">Agent</option>
              <option value="admin">Admin</option>
              <option value="owner">Owner</option>
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setInviteOpen(false)} className="btn-secondary">
              Cancel
            </button>
            <button
              onClick={inviteMember}
              disabled={saving || !inviteEmail.trim()}
              className="btn-primary"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Send invite
            </button>
          </div>
        </div>
      </Modal>

      {/* Add webhook */}
      <Modal open={hookOpen} onClose={() => setHookOpen(false)} title="Add webhook">
        <div className="space-y-4">
          <div>
            <label className="label">Endpoint URL</label>
            <input
              type="url"
              value={hookUrl}
              onChange={(e) => setHookUrl(e.target.value)}
              className="input"
              placeholder="https://example.com/hooks/lumio"
              autoFocus
            />
            <p className="text-xs text-ink-400 mt-1">
              Subscribed to <code>message.created</code> and{' '}
              <code>conversation.escalated</code>.
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setHookOpen(false)} className="btn-secondary">
              Cancel
            </button>
            <button
              onClick={createWebhook}
              disabled={saving || !hookUrl.trim()}
              className="btn-primary"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Create
            </button>
          </div>
        </div>
      </Modal>

      {/* Create API key */}
      <Modal
        open={keyOpen}
        onClose={() => {
          setKeyOpen(false)
          setNewKey(null)
        }}
        title={newKey ? 'API key created' : 'Create API key'}
      >
        {newKey ? (
          <div className="space-y-4">
            <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl p-3">
              <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-amber-800">
                Copy this now — it's shown once and can't be retrieved later.
              </p>
            </div>
            <div className="flex items-center gap-2 bg-ink-50 rounded-xl p-3 border border-ink-200">
              <code className="text-xs text-ink-800 flex-1 break-all font-mono">{newKey}</code>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(newKey)
                  setCopied(true)
                  toast.success('API key copied')
                  setTimeout(() => setCopied(false), 2000)
                }}
                className="flex-shrink-0 p-1.5 text-ink-400 hover:text-ink-600"
                aria-label="Copy API key"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-500" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
            <div className="flex justify-end">
              <button
                onClick={() => {
                  setKeyOpen(false)
                  setNewKey(null)
                }}
                className="btn-primary"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="label">Key name</label>
              <input
                type="text"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                className="input"
                placeholder="Production server"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setKeyOpen(false)} className="btn-secondary">
                Cancel
              </button>
              <button onClick={createApiKey} disabled={saving} className="btn-primary">
                {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                Create key
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
