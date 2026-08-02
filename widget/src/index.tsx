import React from 'react'
import ReactDOM from 'react-dom/client'
import Widget from './Widget'

// Find the script tag to extract bot_id
const script = document.currentScript as HTMLScriptElement
const botId = script?.getAttribute('data-bot-id') || new URL(script?.src || '').searchParams.get('bot') || ''

// Create container
const container = document.createElement('div')
container.id = 'botforge-widget-root'
document.body.appendChild(container)

// Mount widget
const root = ReactDOM.createRoot(container)
root.render(
  <React.StrictMode>
    <Widget botId={botId} />
  </React.StrictMode>
)
