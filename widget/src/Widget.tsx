import { useState, useEffect } from 'react'
import ChatWindow from './ChatWindow'
import PoweredBy from './PoweredBy'
import { fetchWidgetConfig, WidgetConfig } from './api'

interface WidgetProps {
  botId: string
}

export default function Widget({ botId }: WidgetProps) {
  const [open, setOpen] = useState(false)
  const [config, setConfig] = useState<WidgetConfig | null>(null)

  useEffect(() => {
    fetchWidgetConfig(botId).then(setConfig).catch(console.error)
  }, [botId])

  if (!config) return null

  const position = config.position === 'bottom-left' ? { left: '20px' } : { right: '20px' }

  return (
    <>
      <style>{getStyles(config)}</style>

      {/* Chat Window */}
      {open && (
        <div className="bf-window" style={{ ...position, bottom: '90px' }}>
          <div className="bf-header">
            <div className="bf-header-info">
              {config.avatar_url && <img src={config.avatar_url} className="bf-avatar" alt="" />}
              <div>
                <div className="bf-bot-name">{config.bot_name}</div>
                <div className="bf-status">Online</div>
              </div>
            </div>
            <button className="bf-close" onClick={() => setOpen(false)}>
              &times;
            </button>
          </div>
          <ChatWindow botId={botId} config={config} />
          {config.show_powered_by && <PoweredBy />}
        </div>
      )}

      {/* Bubble */}
      <button
        className="bf-bubble"
        style={{ ...position, bottom: '20px', backgroundColor: config.primary_color }}
        onClick={() => setOpen(!open)}
      >
        {open ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>
    </>
  )
}

function getStyles(config: WidgetConfig) {
  return `
    #botforge-widget-root * {
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      margin: 0;
      padding: 0;
    }
    .bf-bubble {
      position: fixed;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 99999;
      transition: transform 0.2s;
    }
    .bf-bubble:hover { transform: scale(1.1); }
    .bf-window {
      position: fixed;
      width: ${config.width}px;
      height: ${config.height}px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.12);
      z-index: 99999;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid #e5e7eb;
    }
    .bf-header {
      background: ${config.primary_color};
      color: ${config.text_color};
      padding: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .bf-header-info { display: flex; align-items: center; gap: 10px; }
    .bf-avatar { width: 36px; height: 36px; border-radius: 50%; }
    .bf-bot-name { font-weight: 600; font-size: 15px; }
    .bf-status { font-size: 12px; opacity: 0.8; }
    .bf-close {
      background: none;
      border: none;
      color: ${config.text_color};
      font-size: 24px;
      cursor: pointer;
      opacity: 0.8;
    }
    .bf-close:hover { opacity: 1; }
    .bf-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .bf-msg { max-width: 80%; padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.4; }
    .bf-msg-customer {
      background: ${config.primary_color};
      color: ${config.text_color};
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }
    .bf-msg-bot {
      background: #f3f4f6;
      color: #1f2937;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
    }
    .bf-source {
      font-size: 11px;
      color: #6366f1;
      margin-top: 4px;
      cursor: pointer;
    }
    .bf-typing {
      align-self: flex-start;
      display: flex;
      gap: 4px;
      padding: 10px 14px;
      background: #f3f4f6;
      border-radius: 16px;
    }
    .bf-dot {
      width: 6px; height: 6px;
      background: #9ca3af;
      border-radius: 50%;
      animation: bf-bounce 1.4s infinite;
    }
    .bf-dot:nth-child(2) { animation-delay: 0.15s; }
    .bf-dot:nth-child(3) { animation-delay: 0.3s; }
    @keyframes bf-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }
    .bf-input-area {
      padding: 12px;
      border-top: 1px solid #e5e7eb;
      display: flex;
      gap: 8px;
    }
    .bf-input {
      flex: 1;
      border: 1px solid #e5e7eb;
      border-radius: 24px;
      padding: 10px 16px;
      font-size: 14px;
      outline: none;
    }
    .bf-input:focus { border-color: ${config.primary_color}; }
    .bf-send {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      border: none;
      background: ${config.primary_color};
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .bf-send:disabled { opacity: 0.5; cursor: not-allowed; }
    .bf-powered {
      text-align: center;
      padding: 8px;
      font-size: 11px;
      color: #9ca3af;
      border-top: 1px solid #f3f4f6;
    }
    .bf-powered a { color: #6366f1; text-decoration: none; }
  `
}
