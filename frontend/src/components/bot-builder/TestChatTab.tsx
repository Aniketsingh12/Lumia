import { useState, useRef, useEffect } from 'react'
import { Send, RotateCcw, ThumbsUp, ThumbsDown, Info } from 'lucide-react'
import { useChat } from '../../hooks/useChat'
import MessageBubble from '../chat/MessageBubble'
import TypingIndicator from '../chat/TypingIndicator'
import api from '../../lib/api'
import toast from 'react-hot-toast'

export default function TestChatTab({ botId }: { botId: string }) {
  const { messages, conversationId, sending, send, clearChat } = useChat(botId)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleSend = async () => {
    if (!input.trim() || sending) return
    const msg = input
    setInput('')
    await send(msg)
  }

  return (
    <div className="flex gap-6">
      {/* Chat */}
      <div className="flex-1 card flex flex-col h-[500px]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h3 className="font-medium text-gray-900">Test Chat</h3>
          <button onClick={clearChat} className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1">
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 py-12">
              <p>Send a message to test your bot</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <MessageBubble key={msg.id || i} message={msg} showDebug />
          ))}
          {sending && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-gray-200 p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="input flex-1"
              placeholder="Ask your bot something..."
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button onClick={handleSend} disabled={sending || !input.trim()} className="btn-primary">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Debug panel */}
      <div className="w-72 flex-shrink-0">
        <div className="card p-4">
          <h3 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
            <Info className="w-4 h-4" />
            Debug Info
          </h3>
          {messages.filter((m) => m.role === 'ai').length > 0 ? (
            <div className="space-y-3 text-sm">
              {(() => {
                const lastAi = [...messages].reverse().find((m) => m.role === 'ai')
                if (!lastAi) return null
                return (
                  <>
                    <div>
                      <p className="text-gray-500">Intent</p>
                      <p className="font-medium capitalize">{lastAi.intent || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Confidence</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-primary-500 h-2 rounded-full"
                            style={{ width: `${(lastAi.confidence_score || 0) * 100}%` }}
                          />
                        </div>
                        <span className="font-medium">{((lastAi.confidence_score || 0) * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    {lastAi.source_chunks && lastAi.source_chunks.length > 0 && (
                      <div>
                        <p className="text-gray-500 mb-1">Sources Used</p>
                        {lastAi.source_chunks.map((s: any, i: number) => (
                          <div key={i} className="bg-gray-50 rounded p-2 mb-1 text-xs text-gray-600">
                            {s.content?.slice(0, 100)}...
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="flex gap-2 pt-2 border-t border-gray-100">
                      <button
                        className="flex-1 btn-secondary text-xs flex items-center justify-center gap-1"
                        onClick={async () => {
                          if (!lastAi || !conversationId) return
                          try {
                            await api.post('/chat/feedback', {
                              message_id: lastAi.id,
                              conversation_id: conversationId,
                              rating: 'thumbs_up',
                            })
                            toast.success('Thanks for the feedback!')
                          } catch {
                            toast.error('Could not submit feedback')
                          }
                        }}
                      >
                        <ThumbsUp className="w-3 h-3" /> Good
                      </button>
                      <button
                        className="flex-1 btn-secondary text-xs flex items-center justify-center gap-1"
                        onClick={async () => {
                          if (!lastAi || !conversationId) return
                          try {
                            await api.post('/chat/feedback', {
                              message_id: lastAi.id,
                              conversation_id: conversationId,
                              rating: 'thumbs_down',
                            })
                            toast.success('Feedback recorded')
                          } catch {
                            toast.error('Could not submit feedback')
                          }
                        }}
                      >
                        <ThumbsDown className="w-3 h-3" /> Bad
                      </button>
                    </div>
                  </>
                )
              })()}
            </div>
          ) : (
            <p className="text-sm text-gray-400">Send a message to see debug info</p>
          )}
        </div>
      </div>
    </div>
  )
}
