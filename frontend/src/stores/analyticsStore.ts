import { create } from 'zustand'
import api from '../lib/api'

export interface OverviewStats {
  total_messages: number
  total_conversations: number
  avg_response_time: number
  human_handoffs: number
  satisfaction_score: number
  ai_resolution_rate: number
}

export interface TopQuestion {
  question: string
  count: number
  avg_confidence: number
}

export interface ChannelBreakdown {
  channel: string
  count: number
  percentage: number
}

export interface UnansweredQuestion {
  question: string
  count: number
  last_asked: string
}

interface AnalyticsState {
  overview: OverviewStats | null
  topQuestions: TopQuestion[]
  unanswered: UnansweredQuestion[]
  channelBreakdown: ChannelBreakdown[]
  dateRange: string
  loading: boolean
  error: string | null
  setDateRange: (range: string) => void
  fetchAnalytics: (botId: string) => Promise<void>
}

export const useAnalyticsStore = create<AnalyticsState>((set, get) => ({
  overview: null,
  topQuestions: [],
  unanswered: [],
  channelBreakdown: [],
  dateRange: '7d',
  loading: false,
  error: null,

  setDateRange: (range) => set({ dateRange: range }),

  fetchAnalytics: async (botId) => {
    if (!botId) return
    set({ loading: true, error: null })
    try {
      const range = get().dateRange
      const [overview, topQuestions, unanswered, channels] = await Promise.all([
        api.get(`/analytics/overview?bot_id=${botId}&range=${range}`),
        api.get(`/analytics/top-questions?bot_id=${botId}`),
        api.get(`/analytics/unanswered?bot_id=${botId}`),
        api.get(`/analytics/channels?bot_id=${botId}`),
      ])
      set({
        overview: overview.data,
        topQuestions: topQuestions.data,
        unanswered: unanswered.data,
        channelBreakdown: channels.data,
        loading: false,
      })
    } catch {
      set({ loading: false, error: 'Failed to load analytics' })
    }
  },
}))
