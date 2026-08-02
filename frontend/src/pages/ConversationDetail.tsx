import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Send, Sparkles, CheckCircle } from 'lucide-react'
import { useChatStore, type Message } from '../stores/chatStore'
import { socketManager } from '../lib/socket'
import api from '../lib/api'
import ChatWindow from '../components/chat/ChatWindow'
import AgentPanel from '../components/conversations/AgentPanel'
import HandoffBanner from '../components/conversations/HandoffBanner'
import toast from 'react-hot-toast'

interface Conversation {
  id: string
  bot_id: string
  status: string
  channel: string
  customer_id: string
  customer_name?: string
}

export default function ConversationDetail() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { messages, loadMessages, addMessage } = useChatStore()
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [replyText, setReplyText] = useState('')
  const [sending, setSending] = useState(false)
  // suggestion is kept in state so it can be pre-filled; suppress unused-var lint
  const [, setSuggestion] = useState('')

  useEffect(() => {
    if (!conversationId) return
    loadMessages(conversationId)
    api.get(`/conversations/${conversationId}`).then(({ data }) => {
      setConversation(data.conversation as Conversation)
    }).catch(() => toast.error('Failed to load conversation'))
    socketManager.connect(conversationId)
    const unsub = socketManager.onMessage((data) => {
      if (data.type === 'new_message') addMessage(data.message as Message)
    })
    return () => {
      unsub()
      socketManager.disconnect()
    }
  }, [conversationId, loadMessages, addMessage])

  const handleReply = async () => {
    if (!replyText.trim() || !conversationId) return
    setSending(true)
    try {
      await api.post(`/conversations/${conversationId}/reply`, { content: replyText })
      setReplyText('')
      toast.success('Reply sent')
    } catch {
      toast.error('Failed to send reply')
    }
    setSending(false)
  }

  const handleSuggest = async () => {
    try {
      const { data } = await api.get(`/conversations/${conversationId}/suggest`)
      setSuggestion(data.suggestion as string)
      setReplyText(data.suggestion as string)
    } catch {
      toast.error('Failed to get suggestion')
    }
  }

  const handleResolve = async () => {
    if (!conversation) return
    try {
      await api.patch(`/conversations/${conversationId}/resolve`)
      setConversation({ ...conversation, status: 'resolved' })
      toast.success('Conversation resolved')
    } catch {
      toast.error('Failed to resolve')
    }
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-140px)]">
      {/* Chat area */}
      <div className="flex-1 flex flex-col card">
        {conversation?.status === 'escalated' && (
          <HandoffBanner />
        )}

        <div className="flex-1 overflow-y-auto p-4">
          <ChatWindow messages={messages} />
        </div>

        {/* Agent reply input */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex gap-2 mb-2">
            <button onClick={handleSuggest} className="btn-secondary text-xs flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              AI Suggest
            </button>
            <button onClick={handleResolve} className="btn-secondary text-xs flex items-center gap-1">
              <CheckCircle className="w-3 h-3" />
              Resolve
            </button>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              className="input flex-1"
              placeholder="Type your reply..."
              onKeyDown={(e) => e.key === 'Enter' && handleReply()}
            />
            <button onClick={handleReply} disabled={sending} className="btn-primary">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Agent Panel */}
      <div className="w-80 flex-shrink-0">
        <AgentPanel conversation={conversation} />
      </div>
    </div>
  )
}
