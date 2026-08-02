import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow } from 'date-fns'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date) {
  return format(new Date(date), 'MMM d, yyyy')
}

export function formatTime(date: string | Date) {
  return format(new Date(date), 'h:mm a')
}

export function formatRelative(date: string | Date) {
  return formatDistanceToNow(new Date(date), { addSuffix: true })
}

export function formatFileSize(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function truncate(str: string, length: number) {
  if (str.length <= length) return str
  return str.slice(0, length) + '...'
}

export function getChannelIcon(channel: string) {
  const icons: Record<string, string> = {
    website: '🌐',
    whatsapp: '📱',
    instagram: '📸',
    slack: '💬',
    email: '📧',
  }
  return icons[channel] || '💬'
}

export function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    resolved: 'bg-gray-100 text-gray-800',
    escalated: 'bg-red-100 text-red-800',
    processing: 'bg-yellow-100 text-yellow-800',
    ready: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    draft: 'bg-gray-100 text-gray-600',
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}
