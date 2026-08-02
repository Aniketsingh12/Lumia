import { FileText } from 'lucide-react'

interface SourceCitationProps {
  source: {
    content?: string
    metadata?: Record<string, string | number | boolean>
  }
  index: number
}

export default function SourceCitation({ source, index }: SourceCitationProps) {
  const raw = source.content || ''
  const preview = raw.slice(0, 80)
  const needsEllipsis = raw.length > 80

  return (
    <div className="inline-flex items-center gap-1.5 bg-blue-50 text-blue-700 rounded-md px-2 py-1 text-xs mr-1 mt-1">
      <FileText className="w-3 h-3" />
      <span>
        Source {index}: {preview || 'Source document'}
        {needsEllipsis ? '…' : ''}
      </span>
    </div>
  )
}
