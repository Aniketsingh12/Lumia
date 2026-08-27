import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { BookOpen, User, Globe, MessageSquare, Power } from 'lucide-react'
import { useBot } from '../hooks/useBots'
import { cn } from '../lib/utils'
import KnowledgeTab from '../components/bot-builder/KnowledgeTab'
import PersonalityTab from '../components/bot-builder/PersonalityTab'
import ChannelsTab from '../components/bot-builder/ChannelsTab'
import TestChatTab from '../components/bot-builder/TestChatTab'
import toast from 'react-hot-toast'
import { useBotStore } from '../stores/botStore'

const tabs = [
  { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
  { id: 'personality', label: 'Personality', icon: User },
  { id: 'channels', label: 'Channels', icon: Globe },
  { id: 'test', label: 'Test Chat', icon: MessageSquare },
]

export default function BotBuilder() {
  const { botId } = useParams<{ botId: string }>()
  const { bot, loading } = useBot(botId!)
  const { toggleBot } = useBotStore()
  const [activeTab, setActiveTab] = useState('knowledge')

  if (loading || !bot) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    )
  }

  const handleToggle = async () => {
    try {
      await toggleBot(bot.id)
      toast.success(bot.is_active ? 'Bot deactivated' : 'Bot activated!')
    } catch {
      toast.error('Failed to toggle bot')
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{bot.name}</h1>
          <p className="text-gray-500 mt-1">Configure your bot's knowledge, personality, and channels</p>
        </div>
        <button
          onClick={handleToggle}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
            bot.is_active
              ? 'bg-green-500/15 text-green-300 hover:bg-green-200'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          )}
        >
          <Power className="w-4 h-4" />
          {bot.is_active ? 'Active' : 'Inactive'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.id
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'knowledge' && <KnowledgeTab botId={bot.id} />}
      {activeTab === 'personality' && <PersonalityTab bot={bot} />}
      {activeTab === 'channels' && <ChannelsTab bot={bot} />}
      {activeTab === 'test' && <TestChatTab botId={bot.id} />}
    </div>
  )
}
