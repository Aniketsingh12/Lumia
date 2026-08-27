import { AlertCircle } from 'lucide-react'

interface GapsTableProps {
  questions: { question: string; count: number; first_asked?: string }[]
}

export default function GapsTable({ questions }: GapsTableProps) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-4">
        <AlertCircle className="w-5 h-5 text-amber-500" />
        <h3 className="font-semibold text-gray-900">Knowledge Gaps — Unanswered Questions</h3>
      </div>
      {questions.length === 0 ? (
        <p className="text-gray-400 text-sm py-4 text-center">No unanswered questions found</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 px-3 text-gray-500 font-medium">Question</th>
                <th className="text-right py-2 px-3 text-gray-500 font-medium">Times Asked</th>
              </tr>
            </thead>
            <tbody>
              {questions.map((q, i) => (
                <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-2.5 px-3 text-gray-700">{q.question}</td>
                  <td className="py-2.5 px-3 text-right">
                    <span className="px-2 py-0.5 bg-amber-500/15 text-amber-300 rounded-full text-xs font-medium">
                      {q.count}x
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-gray-400 mt-3">
            Upload documents covering these topics to improve your bot's responses.
          </p>
        </div>
      )}
    </div>
  )
}
