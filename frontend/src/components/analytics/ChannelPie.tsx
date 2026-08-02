import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { getChannelIcon } from '../../lib/utils'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

interface ChannelPieProps {
  data: { channel: string; count: number; percentage: number }[]
}

export default function ChannelPie({ data }: ChannelPieProps) {
  return (
    <div className="card p-5">
      <h3 className="font-semibold text-gray-900 mb-4">Channel Breakdown</h3>
      {data.length === 0 ? (
        <p className="text-gray-400 text-sm py-8 text-center">No data yet</p>
      ) : (
        <>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  dataKey="count"
                  nameKey="channel"
                  label={({ channel, percentage }) => `${channel} ${percentage}%`}
                >
                  {data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '13px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2 mt-4">
            {data.map((item, i) => (
              <div key={item.channel} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                  <span>{getChannelIcon(item.channel)} {item.channel}</span>
                </div>
                <span className="font-medium">{item.percentage}%</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
