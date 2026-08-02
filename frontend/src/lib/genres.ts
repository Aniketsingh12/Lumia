import {
  Headphones,
  TrendingUp,
  CalendarCheck,
  GraduationCap,
  Code2,
  Drama,
  type LucideIcon,
} from 'lucide-react'

// Mirrors backend/app/services/bot_genres.py — keep the ids in sync.
// The backend owns prompt behavior; this file owns display copy and icons.
export interface BotGenre {
  id: string
  label: string
  description: string
  icon: LucideIcon
  // Character bots use the persona field as their whole identity
  usesPersona: boolean
  personaPlaceholder?: string
}

export const BOT_GENRES: BotGenre[] = [
  {
    id: 'support',
    label: 'Customer Support',
    description: 'Answers questions from your docs, escalates to humans when unsure',
    icon: Headphones,
    usesPersona: false,
  },
  {
    id: 'sales',
    label: 'Sales Assistant',
    description: 'Highlights product benefits and guides customers toward a purchase',
    icon: TrendingUp,
    usesPersona: false,
  },
  {
    id: 'booking',
    label: 'Booking Concierge',
    description: 'Handles reservations, availability checks, and scheduling details',
    icon: CalendarCheck,
    usesPersona: false,
  },
  {
    id: 'tutor',
    label: 'Tutor',
    description: 'Teaches step by step from your course material and general knowledge',
    icon: GraduationCap,
    usesPersona: false,
  },
  {
    id: 'coding',
    label: 'Coding Assistant',
    description: 'Answers programming questions with code examples from your docs',
    icon: Code2,
    usesPersona: false,
  },
  {
    id: 'character',
    label: 'Character / Companion',
    description: 'A casual chat character with any personality you describe',
    icon: Drama,
    usesPersona: true,
    personaPlaceholder:
      'e.g., A cheerful pirate captain who speaks in nautical slang and loves telling sea stories',
  },
]

export function getGenre(id?: string): BotGenre {
  return BOT_GENRES.find((g) => g.id === id) || BOT_GENRES[0]
}
