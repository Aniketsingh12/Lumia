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
    { label: 'Messages', value: stats.total_messages.toLocaleString(), icon: MessageSquare, color: 'text-blue-600 bg-blue-50' },
    { label: 'Conversations', value: stats.total_conversations.toLocaleString(), icon: Users, color: 'text-purple-600 bg-purple-50' },
    { label: 'AI Resolution', value: `${(stats.ai_resolution_rate * 100).toFixed(0)}%`, icon: Zap, color: 'text-green-600 bg-green-50' },
    { label: 'Avg Response', value: `${stats.avg_response_time}s`, icon: Clock, color: 'text-yellow-600 bg-yellow-50' },
    { label: 'Handoffs', value: stats.human_handoffs.toString(), icon: AlertTriangle, color: 'text-red-600 bg-red-50' },
    { label: 'Satisfaction', value: `${stats.satisfaction_score}/5`, icon: ThumbsUp, color: 'text-emerald-600 bg-emerald-50' },
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
