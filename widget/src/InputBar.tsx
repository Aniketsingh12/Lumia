import { useState } from 'react'

interface InputBarProps {
  onSend: (text: string) => void
  disabled: boolean
}

export default function InputBar({ onSend, disabled }: InputBarProps) {
  const [text, setText] = useState('')

  const handleSubmit = () => {
    if (!text.trim() || disabled) return
    onSend(text.trim())
    setText('')
  }

  return (
    <div className="bf-input-area">
      <input
        className="bf-input"
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        placeholder="Type a message..."
        disabled={disabled}
      />
      <button className="bf-send" onClick={handleSubmit} disabled={disabled || !text.trim()}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>
  )
}
