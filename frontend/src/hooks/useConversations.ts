import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

interface Conversation {
  id: string
  bot_id: string
  channel: string
  customer_name?: string
  status: string
  last_message?: string
  message_count: number
  started_at?: string
}

export function useConversations(botId?: string, status?: string) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(false)

  const fetchConversations = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (botId) params.set('bot_id', botId)
      if (status) params.set('status', status)
      const { data } = await api.get(`/conversations/?${params}`)
      setConversations(data)
    } catch (e) {
      console.error('Failed to fetch conversations', e)
    }
    setLoading(false)
  }, [botId, status])

  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  return { conversations, loading, refetch: fetchConversations }
}
