import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

/**
 * shadcn/ui-style Button.
 *
 * Kept separate from the older `components/common/Button.tsx` (which has its own
 * loading/icon API used across the dashboard) so neither has to change. Use this
 * one for marketing surfaces — it carries the landing-page variants.
 */
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-all ' +
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ' +
    'focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground rounded-lg hover:brightness-110 active:scale-[0.97]',
        secondary: 'bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 active:scale-[0.97]',
        outline:
          'border border-border bg-transparent text-foreground rounded-lg hover:bg-secondary active:scale-[0.97]',
        ghost: 'bg-transparent text-muted-foreground rounded-lg hover:text-foreground hover:bg-secondary',
        destructive: 'bg-destructive text-destructive-foreground rounded-lg hover:brightness-110',
        /** Navbar call-to-action — muted chip that lifts slightly on press. */
        navCta:
          'text-foreground bg-nav-button hover:bg-nav-button/80 active:scale-[0.97] transition-all rounded-lg',
        /** Solid green hero CTA. */
        hero:
          'bg-primary text-primary-foreground rounded-sm hover:brightness-110 active:scale-[0.97] font-bold',
        /** White counterpart to `hero`, for the secondary action. */
        heroOutline:
          'bg-white text-background rounded-sm hover:brightness-90 active:scale-[0.97] font-bold',
      },
      size: {
        default: 'h-10 px-4 py-2 text-sm',
        sm: 'h-9 px-3 text-xs',
        lg: 'h-11 px-8 text-sm',
        xl: 'px-8 py-4 text-sm',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  )
)
Button.displayName = 'Button'

export { Button, buttonVariants }
