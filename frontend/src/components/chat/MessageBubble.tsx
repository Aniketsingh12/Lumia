import { Bot, User, Headphones } from 'lucide-react'
import { cn, formatTime } from '../../lib/utils'
import SourceCitation from './SourceCitation'

interface MessageBubbleProps {
  message: {
    role: 'customer' | 'ai' | 'agent'
    content: string
    source_chunks?: any[]
    confidence_score?: number
    intent?: string
    created_at?: string
  }
  showDebug?: boolean
}

export default function MessageBubble({ message, showDebug }: MessageBubbleProps) {
  const isCustomer = message.role === 'customer'
  const isAgent = message.role === 'agent'

  // Strip confidence tag from display
  const displayContent = message.content.replace(/\[Confidence:\s*\d+\/10\]/g, '').trim()

  return (
    <div className={cn('flex gap-3', isCustomer ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          isCustomer ? 'bg-gray-200' : isAgent ? 'bg-orange-100' : 'bg-primary-100'
        )}
      >
        {isCustomer ? (
          <User className="w-4 h-4 text-gray-600" />
        ) : isAgent ? (
          <Headphones className="w-4 h-4 text-orange-600" />
        ) : (
          <Bot className="w-4 h-4 text-primary-600" />
        )}
      </div>

      {/* Bubble */}
      <div className={cn('max-w-[75%]')}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm',
            isCustomer
              ? 'bg-primary-600 text-white rounded-tr-sm'
              : isAgent
              ? 'bg-orange-50 text-gray-900 border border-orange-200 rounded-tl-sm'
              : 'bg-gray-100 text-gray-900 rounded-tl-sm'
          )}
        >
          <p className="whitespace-pre-wrap">{displayContent}</p>
        </div>

        {/* Sources */}
        {!isCustomer && message.source_chunks && message.source_chunks.length > 0 && (
          <div className="mt-1.5">
            {message.source_chunks.slice(0, 2).map((source: any, i: number) => (
              <SourceCitation key={i} source={source} index={i + 1} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        {message.created_at && (
          <p className={cn('text-xs mt-1', isCustomer ? 'text-right' : 'text-left', 'text-gray-400')}>
            {formatTime(message.created_at)}
            {isAgent && ' (Agent)'}
          </p>
        )}
      </div>
    </div>
  )
}
