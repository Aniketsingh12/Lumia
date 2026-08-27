import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '../../lib/utils'

interface RevealProps {
  children: ReactNode
  /** Stagger in seconds, applied once the element enters the viewport. */
  delay?: number
  className?: string
}

/**
 * Plays the `fade-up` animation when the element first scrolls into view.
 *
 * The hero can animate on mount because it's above the fold, but everything
 * below it would otherwise finish animating while still off-screen and appear
 * static by the time the user arrives.
 *
 * Falls back to visible-without-animation if IntersectionObserver is missing,
 * so content is never trapped at opacity-0.
 */
export default function Reveal({ children, delay = 0, className }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [shown, setShown] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (typeof IntersectionObserver === 'undefined') {
      setShown(true)
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true)
          observer.disconnect() // reveal once; don't re-hide on scroll-out
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -60px 0px' }
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={cn(shown ? 'animate-fade-up' : 'opacity-0', className)}
      style={shown && delay ? { animationDelay: `${delay}s` } : undefined}
    >
      {children}
    </div>
  )
}
