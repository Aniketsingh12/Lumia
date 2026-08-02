import { getChannelIcon, formatRelative, truncate } from '../../lib/utils'
import Badge from '../common/Badge'

interface ConversationCardProps {
  conversation: {
    id: string
    channel: string
    customer_name?: string
    status: string
    last_message?: string
    message_count: number
    started_at?: string
  }
  onClick: () => void
}

export default function ConversationCard({ conversation, onClick }: ConversationCardProps) {
  return (
    <div
      onClick={onClick}
      className="card p-4 cursor-pointer hover:border-primary-200 hover:shadow-sm transition-all"
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">{getChannelIcon(conversation.channel)}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-900">
              {conversation.customer_name || 'Anonymous'}
            </span>
            <Badge status={conversation.status}>{conversation.status}</Badge>
          </div>
          <p className="text-sm text-gray-500 truncate mt-1">
            {truncate(conversation.last_message || 'No messages', 80)}
          </p>
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
            <span>{conversation.message_count} messages</span>
            {conversation.started_at && <span>{formatRelative(conversation.started_at)}</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
