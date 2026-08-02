import { useEffect, useCallback } from 'react'
import { useChatStore, type Message } from '../stores/chatStore'
import { socketManager } from '../lib/socket'

export function useChat(botId: string) {
  const { messages, conversationId, sending, sendMessage, clearChat, addMessage } = useChatStore()

  useEffect(() => {
    if (conversationId) {
      socketManager.connect(conversationId)
      const unsubscribe = socketManager.onMessage((data) => {
        if (data.type === 'new_message') {
          addMessage(data.message as Message)
        }
      })
      return () => {
        unsubscribe()
        socketManager.disconnect()
      }
    }
  }, [conversationId, addMessage])

  const send = useCallback(
    (message: string) => {
      return sendMessage(botId, message, conversationId || undefined)
    },
    [botId, conversationId, sendMessage]
  )

  return { messages, conversationId, sending, send, clearChat }
}
