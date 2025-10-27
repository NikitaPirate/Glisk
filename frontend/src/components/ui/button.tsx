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
          'bg-[#FFBB00] text-black font-bold shadow-[6px_6px_0px_0px_#000000] hover:shadow-[3px_3px_0px_0px_#000000] active:shadow-[3px_3px_0px_0px_#000000] active:translate-x-[3px] active:translate-y-[3px]',
        destructive:
          'text-red-500 dark:text-red-400 font-semibold hover:text-red-600 dark:hover:text-red-300',
        outline:
          'text-blue-500 dark:text-blue-400 font-medium hover:text-blue-600 dark:hover:text-blue-300',
        secondary:
          'text-cyan-500 dark:text-cyan-400 font-medium shadow-[6px_6px_0px_0px_#000000] hover:shadow-[3px_3px_0px_0px_#000000] active:shadow-[3px_3px_0px_0px_#000000] active:translate-x-[3px] active:translate-y-[3px]',
        ghost:
          'text-purple-600 dark:text-purple-400 font-medium hover:text-purple-700 dark:hover:text-purple-300 shadow-[2px_2px_0px_0px_#000000]',
        'tab-active':
          'text-purple-500 dark:text-purple-300 font-semibold hover:text-purple-600 dark:hover:text-purple-200 shadow-[2px_2px_0px_0px_#000000]',
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
