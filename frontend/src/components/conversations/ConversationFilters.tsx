interface ConversationFiltersProps {
  status?: string
  channel?: string
  onStatusChange: (status: string | undefined) => void
  onChannelChange: (channel: string | undefined) => void
}

export default function ConversationFilters({
  status,
  channel,
  onStatusChange,
  onChannelChange,
}: ConversationFiltersProps) {
  return (
    <div className="flex items-center gap-3">
      <select
        value={status || ''}
        onChange={(e) => onStatusChange(e.target.value || undefined)}
        className="input w-36"
      >
        <option value="">All Status</option>
        <option value="active">Active</option>
        <option value="escalated">Escalated</option>
        <option value="resolved">Resolved</option>
      </select>
      <select
        value={channel || ''}
        onChange={(e) => onChannelChange(e.target.value || undefined)}
        className="input w-36"
      >
        <option value="">All Channels</option>
        <option value="website">Website</option>
        <option value="whatsapp">WhatsApp</option>
        <option value="instagram">Instagram</option>
        <option value="slack">Slack</option>
        <option value="email">Email</option>
      </select>
    </div>
  )
}
