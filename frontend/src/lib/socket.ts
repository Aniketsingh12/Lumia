const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// Derive WebSocket URL from the API URL (http→ws, https→wss)
const WS_URL = API_URL.replace(/^https?/, (p: string) => (p === 'https' ? 'wss' : 'ws'))

type MessageHandler = (data: Record<string, unknown>) => void

class SocketManager {
  private ws: WebSocket | null = null
  private handlers: MessageHandler[] = []
  private conversationId: string | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private intentionalClose = false

  connect(conversationId: string) {
    this.disconnect()
    this.intentionalClose = false
    this.conversationId = conversationId

    this.ws = new WebSocket(`${WS_URL}/api/chat/ws/${conversationId}`)

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>
        this.handlers.forEach((handler) => handler(data))
      } catch {
        // ignore malformed frames
      }
    }

    this.ws.onclose = () => {
      if (this.intentionalClose) return
      // Auto-reconnect after 3 seconds on unexpected close
      this.reconnectTimer = setTimeout(() => {
        if (this.conversationId) {
          this.connect(this.conversationId)
        }
      }, 3000)
    }
  }

  disconnect() {
    this.intentionalClose = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.conversationId = null
  }

  send(data: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  onMessage(handler: MessageHandler) {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler)
    }
  }
}

export const socketManager = new SocketManager()
