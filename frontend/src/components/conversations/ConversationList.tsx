import { getChannelIcon, formatRelative, truncate } from '../../lib/utils'
import Badge from '../common/Badge'

interface Conversation {
  id: string
  channel: string
  customer_name?: string
  status: string
  last_message?: string
  started_at?: string
}

interface ConversationListProps {
  conversations: Conversation[]
  selectedId?: string
  onSelect: (id: string) => void
}

export default function ConversationList({ conversations, selectedId, onSelect }: ConversationListProps) {
  return (
    <div className="divide-y divide-gray-100">
      {conversations.map((conv) => (
        <div
          key={conv.id}
          onClick={() => onSelect(conv.id)}
          className={`flex items-center gap-3 p-3 cursor-pointer transition-colors ${
            selectedId === conv.id ? 'bg-primary-50' : 'hover:bg-gray-50'
          }`}
        >
          <span className="text-xl">{getChannelIcon(conv.channel)}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-900 truncate">
                {conv.customer_name || 'Anonymous'}
              </span>
              <Badge status={conv.status}>{conv.status}</Badge>
            </div>
            <p className="text-xs text-gray-500 truncate mt-0.5">
              {truncate(conv.last_message || '', 50)}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
