interface SourceLinkProps {
  source: { content?: string; metadata?: Record<string, any> }
  index: number
}

export default function SourceLink({ source, index }: SourceLinkProps) {
  const preview = source.content?.slice(0, 60) || 'Source document'

  return (
    <div className="bf-source">
      Source {index}: {preview}...
    </div>
  )
}
