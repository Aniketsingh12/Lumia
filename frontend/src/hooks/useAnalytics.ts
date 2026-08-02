import { useEffect } from 'react'
import { useAnalyticsStore } from '../stores/analyticsStore'

export function useAnalytics(botId: string) {
  const store = useAnalyticsStore()

  useEffect(() => {
    if (botId) {
      store.fetchAnalytics(botId)
    }
  }, [botId, store.dateRange])

  return store
}
