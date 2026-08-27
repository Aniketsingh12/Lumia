import { AlertTriangle } from 'lucide-react'

export default function HandoffBanner() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-amber-500/10 border-b border-amber-500/30">
      <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-amber-300">Human Handoff Active</p>
        <p className="text-xs text-amber-400">AI was unable to resolve this conversation. Agent takeover required.</p>
      </div>
    </div>
  )
}
