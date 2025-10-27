import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-none text-sm font-medium cursor-pointer transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-ring/50 focus-visible:ring-2",
  {
    variants: {
      variant: {
        default: 'text-[#FFBB00] font-semibold hover:text-[#E6A800]',
        'primary-action':
          'bg-[#FFBB00] text-black font-bold shadow-interactive-lg hover-lift-lg active-press-lg',
        destructive:
          'text-red-500 dark:text-red-400 font-semibold hover:text-red-600 dark:hover:text-red-300',
        secondary:
          'bg-secondary text-secondary-foreground font-medium shadow-interactive-lg hover-lift-lg active-press-lg',
        ghost: 'bg-secondary text-secondary-foreground font-medium shadow-interactive hover-lift',
        'tab-active':
          'bg-secondary text-secondary-foreground font-medium shadow-interactive-sm translate-x-[2px] translate-y-[2px]',
        link: 'text-[#FFBB00] underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2 has-[>svg]:px-3',
        sm: 'h-8 gap-1.5 px-3 has-[>svg]:px-2.5',
        lg: 'h-10 px-6 has-[>svg]:px-4',
        xl: 'h-12 px-8 py-4 text-lg',
        icon: 'size-9',
        'icon-sm': 'size-8',
        'icon-lg': 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : 'button'

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { Button, buttonVariants }
