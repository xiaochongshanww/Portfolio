<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cva } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        outline: 'text-foreground',
        accent: 'border-amber-300 bg-amber-50 text-accent-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

type Variant = 'default' | 'secondary' | 'outline' | 'accent'

type BadgeProps = {
  variant?: Variant
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<BadgeProps>(), {
  variant: 'default',
})
</script>

<template>
  <div :class="cn(badgeVariants({ variant }), props.class)">
    <slot />
  </div>
</template>
