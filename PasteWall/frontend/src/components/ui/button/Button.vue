<script setup lang="ts">
import type { ButtonHTMLAttributes } from 'vue'
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent/15 hover:text-accent-foreground',
        ghost: 'hover:bg-secondary hover:text-secondary-foreground',
      },
      size: {
        default: 'h-11 px-5 py-2',
        sm: 'h-11 px-3 text-xs',
        icon: 'h-11 w-11',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

type Variant = 'default' | 'destructive' | 'outline' | 'ghost'
type Size = 'default' | 'sm' | 'icon'

type ButtonProps = {
  variant?: Variant
  size?: Size
  class?: ButtonHTMLAttributes['class']
}

const props = withDefaults(defineProps<ButtonProps>(), {
  variant: 'default',
  size: 'default',
})
</script>

<template>
  <button
    type="button"
    :class="cn(buttonVariants({ variant, size }), props.class)"
  >
    <slot />
  </button>
</template>
