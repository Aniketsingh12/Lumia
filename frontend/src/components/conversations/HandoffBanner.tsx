import { AlertTriangle } from 'lucide-react'

export default function HandoffBanner() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-amber-50 border-b border-amber-200">
      <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-amber-800">Human Handoff Active</p>
        <p className="text-xs text-amber-600">AI was unable to resolve this conversation. Agent takeover required.</p>
      </div>
    </div>
  )
}
