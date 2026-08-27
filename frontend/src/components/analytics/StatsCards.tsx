import { MessageSquare, Users, Zap, Clock, AlertTriangle, ThumbsUp } from 'lucide-react'

interface StatsCardsProps {
  stats: {
    total_messages: number
    total_conversations: number
    ai_resolution_rate: number
    avg_response_time: number
    human_handoffs: number
    satisfaction_score: number
  }
}

export default function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    { label: 'Messages', value: stats.total_messages.toLocaleString(), icon: MessageSquare, color: 'text-blue-400 bg-blue-500/10' },
    { label: 'Conversations', value: stats.total_conversations.toLocaleString(), icon: Users, color: 'text-purple-400 bg-purple-500/10' },
    { label: 'AI Resolution', value: `${(stats.ai_resolution_rate * 100).toFixed(0)}%`, icon: Zap, color: 'text-green-400 bg-green-500/10' },
    { label: 'Avg Response', value: `${stats.avg_response_time}s`, icon: Clock, color: 'text-yellow-400 bg-yellow-500/10' },
    { label: 'Handoffs', value: stats.human_handoffs.toString(), icon: AlertTriangle, color: 'text-red-400 bg-red-500/10' },
    { label: 'Satisfaction', value: `${stats.satisfaction_score}/5`, icon: ThumbsUp, color: 'text-emerald-400 bg-emerald-500/10' },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {cards.map((card) => (
        <div key={card.label} className="card p-4">
          <div className={`w-8 h-8 rounded-lg ${card.color} flex items-center justify-center mb-3`}>
            <card.icon className="w-4 h-4" />
          </div>
          <p className="text-2xl font-bold text-gray-900">{card.value}</p>
          <p className="text-xs text-gray-500 mt-0.5">{card.label}</p>
        </div>
      ))}
    </div>
  )
}
