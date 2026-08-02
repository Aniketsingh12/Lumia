import SourceLink from './SourceLink'

interface MessageBubbleProps {
  message: {
    role: 'customer' | 'ai'
    content: string
    sources?: any[]
  }
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isCustomer = message.role === 'customer'
  const displayContent = message.content.replace(/\[Confidence:\s*\d+\/10\]/g, '').trim()

  return (
    <div className={`bf-msg ${isCustomer ? 'bf-msg-customer' : 'bf-msg-bot'}`}>
      <div>{displayContent}</div>
      {!isCustomer && message.sources && message.sources.length > 0 && (
        <div>
          {message.sources.slice(0, 2).map((source: any, i: number) => (
            <SourceLink key={i} source={source} index={i + 1} />
          ))}
        </div>
      )}
    </div>
  )
}
