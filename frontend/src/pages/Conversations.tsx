import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, Filter } from 'lucide-react'
import { useConversations } from '../hooks/useConversations'
import { getChannelIcon, getStatusColor, formatRelative, truncate } from '../lib/utils'
import Badge from '../components/common/Badge'
import EmptyState from '../components/common/EmptyState'
import ConversationFilters from '../components/conversations/ConversationFilters'

export default function Conversations() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [channelFilter, setChannelFilter] = useState<string | undefined>()
  const { conversations, loading } = useConversations(undefined, statusFilter)
  const navigate = useNavigate()

  const filtered = channelFilter
    ? conversations.filter((c) => c.channel === channelFilter)
    : conversations

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Conversations</h1>
          <p className="text-gray-500 mt-1">{filtered.length} conversations</p>
        </div>
        <ConversationFilters
          status={statusFilter}
          channel={channelFilter}
          onStatusChange={setStatusFilter}
          onChannelChange={setChannelFilter}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={MessageSquare}
          title="No conversations yet"
          description="Conversations will appear here when customers start chatting"
        />
      ) : (
        <div className="card divide-y divide-gray-100">
          {filtered.map((conv) => (
            <div
              key={conv.id}
              onClick={() => navigate(`/conversations/${conv.id}`)}
              className="flex items-center gap-4 p-4 hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <div className="text-2xl">{getChannelIcon(conv.channel)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900">
                    {conv.customer_name || 'Anonymous'}
                  </span>
                  <Badge status={conv.status}>{conv.status}</Badge>
                </div>
                <p className="text-sm text-gray-500 truncate mt-0.5">
                  {truncate(conv.last_message || 'No messages', 80)}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-xs text-gray-400">
                  {conv.started_at ? formatRelative(conv.started_at) : ''}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {conv.message_count} messages
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
