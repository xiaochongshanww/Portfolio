<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    class?: string
    modelValue?: string
    placeholder?: string
    rows?: number
    disabled?: boolean
  }>(),
  { rows: 3 },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
}
</script>

<template>
  <textarea
    :class="cn(
      'flex min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm',
      'placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      'disabled:cursor-not-allowed disabled:opacity-50',
      props.class,
    )"
    :value="props.modelValue"
    :placeholder="props.placeholder"
    :rows="props.rows"
    :disabled="props.disabled"
    @input="onInput"
  />
</template>
