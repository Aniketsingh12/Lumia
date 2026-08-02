import { useState, useRef, useEffect } from 'react'
import { sendMessage, WidgetConfig } from './api'
import MessageBubble from './MessageBubble'
import InputBar from './InputBar'
import TypingDots from './TypingDots'

interface Message {
  id: string
  role: 'customer' | 'ai'
  content: string
  sources?: any[]
}

interface ChatWindowProps {
  botId: string
  config: WidgetConfig
}

export default function ChatWindow({ botId, config }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'greeting',
      role: 'ai',
      content: config.greeting_message,
    },
  ])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (text: string) => {
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'customer',
      content: text,
    }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const response = await sendMessage(botId, text, conversationId)
      setConversationId(response.conversation_id)

      const aiMsg: Message = {
        id: response.message?.id || `ai-${Date.now()}`,
        role: 'ai',
        content: response.message?.content || 'Sorry, I could not process that.',
        sources: response.sources,
      }
      setMessages((prev) => [...prev, aiMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'ai', content: 'Something went wrong. Please try again.' },
      ])
    }
    setLoading(false)
  }

  return (
    <>
      <div className="bf-messages">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {loading && <TypingDots />}
        <div ref={bottomRef} />
      </div>
      <InputBar onSend={handleSend} disabled={loading} />
    </>
  )
}
