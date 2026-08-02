import { getStatusColor } from '../../lib/utils'

interface BadgeProps {
  status: string
  children: React.ReactNode
}

export default function Badge({ status, children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColor(status)}`}>
      {children}
    </span>
  )
}
