import { cn } from '../../lib/utils'

interface AvatarProps {
  name?: string
  src?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export default function Avatar({ name, src, size = 'md', className }: AvatarProps) {
  const sizes = { sm: 'w-6 h-6 text-xs', md: 'w-8 h-8 text-sm', lg: 'w-12 h-12 text-lg' }

  if (src) {
    return <img src={src} alt={name} className={cn('rounded-full object-cover', sizes[size], className)} />
  }

  return (
    <div className={cn('rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-semibold', sizes[size], className)}>
      {name?.charAt(0)?.toUpperCase() || '?'}
    </div>
  )
}
