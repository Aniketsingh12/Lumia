import { create } from 'zustand'
import api from '../lib/api'

/**
 * One channel's saved state as returned by the API.
 *
 * Secrets are never sent to the browser: the backend replaces each secret field
 * with a `<key>_set: true` flag, so the UI can show "configured" without ever
 * holding a token. Non-secret identifiers (phone_number_id, address, …) come
 * through as-is, which is why values are typed loosely here.
 */
export interface ChannelState {
  connected?: boolean
  [key: string]: boolean | string | undefined
}

/** Map of channel id -> its saved state, e.g. { website: { connected: true } }. */
export type ChannelConfig = Record<string, ChannelState>

export interface Bot {
  id: string
  org_id: string
  name: string
  // Genre: support | sales | booking | tutor | coding | character
  bot_type: string
  // Character/persona description (mainly for "character" bots)
  persona?: string | null
  tone: string
  greeting_message: string
  fallback_message: string
  custom_rules: string[]
  // Advanced: full custom system prompt that replaces the genre preset
  system_prompt_override?: string | null
  channels: ChannelConfig
  avatar_url?: string
  is_active: boolean
  message_count: number
  doc_count: number
  created_at?: string
  updated_at?: string
}

interface BotState {
  bots: Bot[]
  currentBot: Bot | null
  loading: boolean
  error: string | null
  fetchBots: () => Promise<void>
  fetchBot: (id: string) => Promise<void>
  createBot: (data: Partial<Bot>) => Promise<Bot>
  updateBot: (id: string, data: Partial<Bot>) => Promise<void>
  deleteBot: (id: string) => Promise<void>
  toggleBot: (id: string) => Promise<void>
}

export const useBotStore = create<BotState>((set, get) => ({
  bots: [],
  currentBot: null,
  loading: false,
  error: null,

  fetchBots: async () => {
    set({ loading: true, error: null })
    try {
      const { data } = await api.get('/bots/')
      set({ bots: data, loading: false })
    } catch (err) {
      set({ loading: false, error: 'Failed to load bots' })
      throw err
    }
  },

  fetchBot: async (id) => {
    set({ loading: true, error: null })
    try {
      const { data } = await api.get(`/bots/${id}`)
      set({ currentBot: data, loading: false })
    } catch (err) {
      set({ loading: false, error: 'Failed to load bot' })
      throw err
    }
  },

  createBot: async (botData) => {
    try {
      const { data } = await api.post('/bots/', botData)
      set({ bots: [...get().bots, data] })
      return data
    } catch (err) {
      throw err
    }
  },

  updateBot: async (id, botData) => {
    try {
      const { data } = await api.put(`/bots/${id}`, botData)
      set({
        currentBot: data,
        bots: get().bots.map((b) => (b.id === id ? data : b)),
      })
    } catch (err) {
      throw err
    }
  },

  deleteBot: async (id) => {
    try {
      await api.delete(`/bots/${id}`)
      set({ bots: get().bots.filter((b) => b.id !== id) })
    } catch (err) {
      throw err
    }
  },

  toggleBot: async (id) => {
    try {
      const { data } = await api.patch(`/bots/${id}/toggle`)
      set({
        currentBot: get().currentBot?.id === id ? data : get().currentBot,
        bots: get().bots.map((b) => (b.id === id ? data : b)),
      })
    } catch (err) {
      throw err
    }
  },
}))
