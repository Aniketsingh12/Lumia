import { useEffect } from 'react'
import { useBotStore } from '../stores/botStore'

export function useBots() {
  const store = useBotStore()

  useEffect(() => {
    if (store.bots.length === 0) {
      store.fetchBots()
    }
  }, [])

  return store
}

export function useBot(botId: string) {
  const { currentBot, fetchBot, updateBot, loading } = useBotStore()

  useEffect(() => {
    if (botId) {
      fetchBot(botId)
    }
  }, [botId])

  return { bot: currentBot, updateBot: (data: any) => updateBot(botId, data), loading }
}
