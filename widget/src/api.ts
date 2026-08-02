// Detect API URL from script tag or default
const script = document.querySelector('script[data-bot-id]') as HTMLScriptElement
const API_URL = script
  ? new URL(script.src).origin
  : 'http://localhost:8000'

export interface WidgetConfig {
  bot_id: string
  bot_name: string
  greeting_message: string
  avatar_url?: string
  tone: string
  primary_color: string
  text_color: string
  position: string
  width: number
  height: number
  show_powered_by: boolean
  auto_open: boolean
  auto_open_delay: number
}

export async function fetchWidgetConfig(botId: string): Promise<WidgetConfig> {
  const response = await fetch(`${API_URL}/api/widget/${botId}/config`)
  if (!response.ok) throw new Error('Failed to fetch widget config')
  return response.json()
}

export async function sendMessage(
  botId: string,
  message: string,
  conversationId: string | null
): Promise<any> {
  const response = await fetch(`${API_URL}/api/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bot_id: botId,
      message,
      conversation_id: conversationId,
      channel: 'website',
    }),
  })
  if (!response.ok) throw new Error('Failed to send message')
  return response.json()
}
