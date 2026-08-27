interface QuickRepliesProps {
  replies: string[]
  onSelect: (reply: string) => void
}

export default function QuickReplies({ replies, onSelect }: QuickRepliesProps) {
  if (replies.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {replies.map((reply) => (
        <button
          key={reply}
          onClick={() => onSelect(reply)}
          className="px-3 py-1.5 bg-secondary border border-primary/30 text-primary rounded-full text-xs font-medium hover:bg-primary/10 transition-colors"
        >
          {reply}
        </button>
      ))}
    </div>
  )
}
