import { User, Clock, Tag, MessageSquare } from 'lucide-react'
import { getChannelIcon, formatRelative } from '../../lib/utils'
import Badge from '../common/Badge'

interface AgentPanelProps {
  conversation: any
}

export default function AgentPanel({ conversation }: AgentPanelProps) {
  if (!conversation) {
    return (
      <div className="card p-4">
        <p className="text-gray-400 text-sm">Loading...</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Customer Info */}
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Customer Info</h3>
        <div className="space-y-2.5">
          <div className="flex items-center gap-2 text-sm">
            <User className="w-4 h-4 text-gray-400" />
            <span className="text-gray-600">{conversation.customer_name || 'Anonymous'}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-lg">{getChannelIcon(conversation.channel)}</span>
            <span className="text-gray-600 capitalize">{conversation.channel}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-gray-400" />
            <span className="text-gray-600">
              {conversation.started_at ? formatRelative(conversation.started_at) : 'N/A'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <MessageSquare className="w-4 h-4 text-gray-400" />
            <span className="text-gray-600">{conversation.message_count || 0} messages</span>
          </div>
        </div>
      </div>

      {/* Status */}
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Status</h3>
        <Badge status={conversation.status}>{conversation.status}</Badge>
        {conversation.ai_resolution !== undefined && (
          <p className="text-xs text-gray-500 mt-2">
            AI resolved: {conversation.ai_resolution ? 'Yes' : 'No'}
          </p>
        )}
      </div>

      {/* Tags */}
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Tags</h3>
        <div className="flex flex-wrap gap-1">
          {(conversation.tags || []).length > 0 ? (
            conversation.tags.map((tag: string) => (
              <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                {tag}
              </span>
            ))
          ) : (
            <span className="text-xs text-gray-400">No tags</span>
          )}
        </div>
      </div>
    </div>
  )
}
