import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface TopQuestionsProps {
  questions: { question: string; count: number }[]
}

export default function TopQuestions({ questions }: TopQuestionsProps) {
  const chartData = questions.slice(0, 7).map((q) => ({
    name: q.question.length > 30 ? q.question.slice(0, 30) + '...' : q.question,
    count: q.count,
  }))

  return (
    <div className="card p-5">
      <h3 className="font-semibold text-gray-900 mb-4">Top Questions</h3>
      {questions.length === 0 ? (
        <p className="text-gray-400 text-sm py-8 text-center">No data yet</p>
      ) : (
        <>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" tick={{ fontSize: 12, fill: '#9ca3af' }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#6b7280' }} width={140} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '13px' }}
                />
                <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 space-y-2">
            {questions.slice(0, 5).map((q, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-gray-700 truncate max-w-[80%]">{i + 1}. {q.question}</span>
                <span className="text-gray-500 font-medium">{q.count}x</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
