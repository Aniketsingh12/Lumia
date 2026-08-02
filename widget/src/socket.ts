const script = document.querySelector('script[data-bot-id]') as HTMLScriptElement
const WS_URL = script
  ? new URL(script.src).origin.replace('http', 'ws')
  : 'ws://localhost:8000'

type Handler = (data: any) => void

export class WidgetSocket {
  private ws: WebSocket | null = null
  private handlers: Handler[] = []

  connect(conversationId: string) {
    this.disconnect()
    this.ws = new WebSocket(`${WS_URL}/api/chat/ws/${conversationId}`)

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handlers.forEach((h) => h(data))
      } catch {}
    }

    this.ws.onclose = () => {
      setTimeout(() => this.connect(conversationId), 3000)
    }
  }

  disconnect() {
    this.ws?.close()
    this.ws = null
  }

  onMessage(handler: Handler) {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler)
    }
  }
}
