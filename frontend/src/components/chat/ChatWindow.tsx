import MessageBubble from './MessageBubble'

interface Message {
  id: string
  role: 'customer' | 'ai' | 'agent'
  content: string
  source_chunks?: any[]
  confidence_score?: number
  created_at?: string
}

export default function ChatWindow({ messages }: { messages: Message[] }) {
  return (
    <div className="space-y-4">
      {messages.map((msg, i) => (
        <MessageBubble key={msg.id || i} message={msg} />
      ))}
    </div>
  )
}
