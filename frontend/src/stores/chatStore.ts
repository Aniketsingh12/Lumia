import { create } from 'zustand'
import toast from 'react-hot-toast'
import api, { getErrorMessage } from '../lib/api'

export interface SourceChunk {
  content?: string
  metadata?: Record<string, string | number | boolean>
}

export interface Message {
  id: string
  conversation_id: string
  role: 'customer' | 'ai' | 'agent'
  content: string
  source_chunks?: SourceChunk[]
  confidence_score?: number
  intent?: string
  created_at?: string
}

interface ChatState {
  messages: Message[]
  conversationId: string | null
  loading: boolean
  sending: boolean
  sendMessage: (botId: string, message: string, conversationId?: string) => Promise<unknown>
  loadMessages: (conversationId: string) => Promise<void>
  addMessage: (message: Message) => void
  clearChat: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  conversationId: null,
  loading: false,
  sending: false,

  sendMessage: async (botId, message, conversationId) => {
    set({ sending: true })

    // Optimistic: insert user message immediately
    const tempId = `temp-${Date.now()}`
    const userMsg: Message = {
      id: tempId,
      conversation_id: conversationId || '',
      role: 'customer',
      content: message,
      created_at: new Date().toISOString(),
    }
    set({ messages: [...get().messages, userMsg] })

    try {
      const { data } = await api.post('/chat/', {
        bot_id: botId,
        message,
        conversation_id: conversationId || get().conversationId,
        channel: 'website',
      })

      // Keep the user's message (now with the real conversation_id) and append
      // the AI reply. The POST /chat/ response only returns the AI message, so
      // we must preserve the optimistic user message rather than drop it.
      set({
        conversationId: data.conversation_id,
        messages: [
          ...get().messages.map((m) =>
            m.id === tempId ? { ...m, conversation_id: data.conversation_id } : m
          ),
          {
            id: data.message.id,
            conversation_id: data.conversation_id,
            role: 'ai' as const,
            content: data.message.content,
            source_chunks: data.sources,
            confidence_score: data.confidence,
            intent: data.intent,
            created_at: new Date().toISOString(),
          },
        ],
        sending: false,
      })

      return data
    } catch (err) {
      // Remove the ghost optimistic message on failure
      set({
        messages: get().messages.filter((m) => m.id !== tempId),
        sending: false,
      })
      toast.error(getErrorMessage(err, 'Failed to send message'))
      throw err
    }
  },

  loadMessages: async (conversationId) => {
    set({ loading: true })
    try {
      const { data } = await api.get(`/conversations/${conversationId}`)
      set({
        messages: data.messages || [],
        conversationId,
        loading: false,
      })
    } catch (err) {
      set({ loading: false })
      toast.error(getErrorMessage(err, 'Failed to load messages'))
    }
  },

  addMessage: (message) => {
    set({ messages: [...get().messages, message] })
  },

  clearChat: () => {
    set({ messages: [], conversationId: null })
  },
}))
