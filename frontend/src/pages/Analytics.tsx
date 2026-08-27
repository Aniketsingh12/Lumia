import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { useAnalytics } from '../hooks/useAnalytics'
import { useBots } from '../hooks/useBots'
import StatsCards from '../components/analytics/StatsCards'
import TopQuestions from '../components/analytics/TopQuestions'
import ChannelPie from '../components/analytics/ChannelPie'
import GapsTable from '../components/analytics/GapsTable'

export default function Analytics() {
  const { bots, loading: botsLoading } = useBots()
  const [selectedBot, setSelectedBot] = useState('')

  // Set the first bot once bots have loaded (avoids the race where useState
  // initialises to '' because bots haven't arrived yet)
  useEffect(() => {
    if (bots.length > 0 && !selectedBot) {
      setSelectedBot(bots[0].id)
    }
  }, [bots, selectedBot])

  const { overview, topQuestions, unanswered, channelBreakdown, dateRange, setDateRange, loading } =
    useAnalytics(selectedBot)

  if (botsLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">Insights into your bot's performance</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedBot}
            onChange={(e) => setSelectedBot(e.target.value)}
            className="input w-48"
          >
            <option value="">Select bot</option>
            {bots.map((bot) => (
              <option key={bot.id} value={bot.id}>
                {bot.name}
              </option>
            ))}
          </select>
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            {['1d', '7d', '30d', '90d'].map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={`px-3 py-1.5 text-sm font-medium ${
                  dateRange === range
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card text-gray-600 hover:bg-gray-50'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      ) : (
        <>
          {overview && <StatsCards stats={overview} />}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            <TopQuestions questions={topQuestions} />
            <ChannelPie data={channelBreakdown} />
          </div>
          <div className="mt-6">
            <GapsTable questions={unanswered} />
          </div>
        </>
      )}
    </div>
  )
}
