import { useState, useEffect, useCallback } from 'react'
import {
  Globe, MessageCircle, Instagram, Hash, Mail, Copy, Check, ExternalLink,
  Loader2, Plug, Trash2, AlertCircle, CheckCircle2,
} from 'lucide-react'
import { type Bot } from '../../stores/botStore'
import api, { getErrorMessage } from '../../lib/api'
import { cn } from '../../lib/utils'
import Modal from '../common/Modal'
import toast from 'react-hot-toast'

interface ChannelsTabProps {
  bot: Bot
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/** Field schema for one channel, served by GET /api/channels/catalog. */
interface CatalogField {
  key: string
  label: string
  secret: boolean
  required: boolean
  generated: boolean
  help: string
  default: string
}

interface CatalogChannel {
  id: string
  label: string
  description: string
  docs_url: string | null
  setup_steps: string[]
  needs_webhook: boolean
  webhook_url: string | null
  fields: CatalogField[]
}

/** Saved state for a channel — secrets arrive as `<key>_set` booleans only. */
type ChannelState = Record<string, string | boolean | undefined>

const ICONS: Record<string, typeof Globe> = {
  website: Globe,
  whatsapp: MessageCircle,
  instagram: Instagram,
  slack: Hash,
  email: Mail,
}

/** Small copy-to-clipboard button used for embed code, webhook URL, tokens. */
function CopyButton({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(value)
        setCopied(true)
        toast.success(`${label || 'Copied'}!`)
        setTimeout(() => setCopied(false), 2000)
      }}
      className="flex-shrink-0 p-1.5 text-gray-400 hover:text-gray-600"
      aria-label={`Copy ${label || 'value'}`}
    >
      {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
    </button>
  )
}

/** Read-only value in a grey box with a copy button (webhook URL, verify token). */
function CopyRow({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-600 mb-1">{label}</p>
      <div className="flex items-center gap-2 bg-gray-50 rounded-lg p-2.5 border border-gray-200">
        <code className="text-xs text-gray-700 flex-1 break-all font-mono">{value}</code>
        <CopyButton value={value} label={label} />
      </div>
      {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
    </div>
  )
}

export default function ChannelsTab({ bot }: ChannelsTabProps) {
  // NOTE: deliberately no fetchBot() after saving. It flips the bot store into
  // `loading`, which makes BotBuilder swap this whole tab for a spinner —
  // unmounting the modal and destroying the one-time verify token the user
  // still needs to copy. load() below already refreshes channel state locally,
  // and the dashboard refetches bots on mount.
  const [catalog, setCatalog] = useState<CatalogChannel[]>([])
  const [channels, setChannels] = useState<Record<string, ChannelState>>({})
  const [loading, setLoading] = useState(true)

  // Modal state
  const [editing, setEditing] = useState<CatalogChannel | null>(null)
  const [form, setForm] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; detail: string } | null>(null)
  // Verify token is returned once on save so the user can paste it into Meta.
  const [freshToken, setFreshToken] = useState<string | null>(null)

  const embedCode = `<script src="${API_URL}/widget.js" data-bot-id="${bot.id}"></script>`

  const load = useCallback(async () => {
    try {
      const [cat, chans] = await Promise.all([
        api.get('/channels/catalog'),
        api.get(`/bots/${bot.id}/channels`),
      ])
      setCatalog(cat.data)
      setChannels(chans.data || {})
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to load channels'))
    } finally {
      setLoading(false)
    }
  }, [bot.id])

  useEffect(() => {
    load()
  }, [load])

  const isConnected = (id: string) => Boolean(channels[id]?.connected)

  const openModal = (channel: CatalogChannel) => {
    // Prefill non-secret fields with saved values; secrets stay blank and are
    // preserved server-side unless the user types a replacement.
    const saved = channels[channel.id] || {}
    const initial: Record<string, string> = {}
    channel.fields.forEach((f) => {
      if (f.secret) initial[f.key] = ''
      else initial[f.key] = String(saved[f.key] ?? f.default ?? '')
    })
    setForm(initial)
    setTestResult(null)
    setFreshToken(null)
    setEditing(channel)
  }

  /** Website needs no credentials — connect/disconnect straight away. */
  const toggleWebsite = async () => {
    try {
      if (isConnected('website')) {
        await api.delete(`/bots/${bot.id}/channels/website`)
        toast.success('Website widget disabled')
      } else {
        await api.put(`/bots/${bot.id}/channels/website`, {})
        toast.success('Website widget enabled')
      }
      await load()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update channel'))
    }
  }

  const handleSave = async () => {
    if (!editing) return
    setSaving(true)
    try {
      const { data } = await api.put(`/bots/${bot.id}/channels/${editing.id}`, form)
      if (data.verify_token) setFreshToken(data.verify_token)
      toast.success(`${editing.label} connected`)
      await load()
      // Keep webhook channels open so the user can copy the verify token.
      if (!editing.needs_webhook) setEditing(null)
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to save credentials'))
    }
    setSaving(false)
  }

  const handleTest = async () => {
    if (!editing) return
    setTesting(true)
    setTestResult(null)
    try {
      const { data } = await api.post(`/bots/${bot.id}/channels/${editing.id}/test`)
      setTestResult(data)
    } catch (err) {
      setTestResult({ ok: false, detail: getErrorMessage(err, 'Test failed') })
    }
    setTesting(false)
  }

  const handleDisconnect = async (channel: CatalogChannel) => {
    try {
      await api.delete(`/bots/${bot.id}/channels/${channel.id}`)
      toast.success(`${channel.label} disconnected`)
      setEditing(null)
      await load()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to disconnect'))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {!bot.is_active && (
        <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
          <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-amber-300">
            This bot is <strong>inactive</strong>. Connected channels won't receive messages
            until you activate it using the toggle at the top of the page.
          </p>
        </div>
      )}

      {catalog.map((channel) => {
        const Icon = ICONS[channel.id] || Plug
        const connected = isConnected(channel.id)
        const saved = channels[channel.id] || {}

        return (
          <div key={channel.id} className="card p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4 min-w-0">
                <div
                  className={cn(
                    'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                    connected ? 'bg-green-500/10' : 'bg-gray-100'
                  )}
                >
                  <Icon className={cn('w-5 h-5', connected ? 'text-green-400' : 'text-gray-600')} />
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900">{channel.label}</h3>
                  <p className="text-sm text-gray-500 mt-0.5">{channel.description}</p>

                  {/* Identifying detail for a connected channel (never a secret) */}
                  {connected && channel.id !== 'website' && (
                    <p className="text-xs text-gray-400 mt-1 font-mono truncate">
                      {String(
                        saved.phone_number_id ||
                          saved.ig_user_id ||
                          saved.address ||
                          saved.team_id ||
                          'credentials saved'
                      )}
                    </p>
                  )}

                  {/* Website embed snippet */}
                  {channel.id === 'website' && connected && (
                    <div className="mt-3">
                      <p className="text-xs text-gray-500 mb-1">Embed code:</p>
                      <div className="flex items-center gap-2 bg-gray-50 rounded-lg p-3">
                        <code className="text-xs text-gray-700 flex-1 break-all font-mono">
                          {embedCode}
                        </code>
                        <CopyButton value={embedCode} label="Embed code" />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {connected && (
                  <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/15 text-green-300">
                    Connected
                  </span>
                )}
                <button
                  onClick={() =>
                    channel.id === 'website' ? toggleWebsite() : openModal(channel)
                  }
                  className={cn(
                    'px-4 py-1.5 rounded-full text-sm font-medium transition-colors',
                    connected
                      ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      : 'bg-primary text-primary-foreground hover:brightness-110'
                  )}
                >
                  {channel.id === 'website'
                    ? connected ? 'Disable' : 'Enable'
                    : connected ? 'Manage' : 'Connect'}
                </button>
              </div>
            </div>
          </div>
        )
      })}

      {/* Credential modal */}
      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={editing ? `Connect ${editing.label}` : ''}
      >
        {editing && (
          <div className="space-y-4">
            {/* Setup steps */}
            {editing.setup_steps.length > 0 && (
              <div className="bg-blue-500/10 border border-blue-500/25 rounded-lg p-3">
                <p className="text-xs font-semibold text-blue-200 mb-1.5">Setup steps</p>
                <ol className="text-xs text-blue-300 space-y-1 list-decimal list-inside">
                  {editing.setup_steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
                {editing.docs_url && (
                  <a
                    href={editing.docs_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-300 font-medium mt-2 hover:underline"
                  >
                    Open provider docs <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            )}

            {/* Credential inputs */}
            {editing.fields
              .filter((f) => !f.generated)
              .map((field) => {
                const alreadySet = Boolean(channels[editing.id]?.[`${field.key}_set`])
                return (
                  <div key={field.key}>
                    <label className="label">
                      {field.label}
                      {field.required && <span className="text-red-500 ml-0.5">*</span>}
                    </label>
                    <input
                      type={field.secret ? 'password' : 'text'}
                      value={form[field.key] ?? ''}
                      onChange={(e) => setForm({ ...form, [field.key]: e.target.value })}
                      className="input"
                      placeholder={
                        field.secret && alreadySet
                          ? '•••••••• (saved — leave blank to keep)'
                          : field.default || ''
                      }
                      autoComplete="off"
                    />
                    {field.help && <p className="text-xs text-gray-400 mt-1">{field.help}</p>}
                  </div>
                )
              })}

            {/* Webhook details — shown after saving so values exist */}
            {editing.needs_webhook && editing.webhook_url && (
              <div className="space-y-3 pt-1 border-t border-gray-100">
                <CopyRow
                  label="Callback URL"
                  value={editing.webhook_url}
                  hint="Paste into the provider's webhook settings. Must be a public HTTPS URL — use ngrok for local testing."
                />
                {freshToken ? (
                  <CopyRow
                    label="Verify token"
                    value={freshToken}
                    hint="Shown once — copy it into the provider now. It stays saved here."
                  />
                ) : (
                  isConnected(editing.id) && (
                    <p className="text-xs text-gray-400">
                      A verify token is already saved. Save again to reveal a fresh one.
                    </p>
                  )
                )}
              </div>
            )}

            {/* Test result */}
            {testResult && (
              <div
                className={cn(
                  'flex items-start gap-2 rounded-lg p-3 text-sm',
                  testResult.ok
                    ? 'bg-green-500/10 border border-green-500/30 text-green-300'
                    : 'bg-red-500/10 border border-red-500/30 text-red-300'
                )}
              >
                {testResult.ok ? (
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                )}
                <span className="break-words">{testResult.detail}</span>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between gap-3 pt-1">
              {isConnected(editing.id) ? (
                <button
                  onClick={() => handleDisconnect(editing)}
                  className="text-sm text-red-400 hover:text-red-300 flex items-center gap-1"
                >
                  <Trash2 className="w-4 h-4" />
                  Disconnect
                </button>
              ) : (
                <span />
              )}
              <div className="flex gap-2">
                {isConnected(editing.id) && (
                  <button
                    onClick={handleTest}
                    disabled={testing}
                    className="btn-secondary flex items-center gap-2"
                  >
                    {testing && <Loader2 className="w-4 h-4 animate-spin" />}
                    Test
                  </button>
                )}
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="btn-primary flex items-center gap-2"
                >
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  Save
                </button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
