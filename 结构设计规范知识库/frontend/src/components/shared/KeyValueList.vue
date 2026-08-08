<template>
  <div class="space-y-2 text-sm">
    <div v-for="(value, key) in data" :key="String(key)">
      <div v-if="isRecord(value)" class="border-t border-slate-100 pt-2 first:border-0 first:pt-0">
        <div class="mb-1 text-xs font-medium text-slate-500">{{ key }}</div>
        <div class="space-y-1 pl-3">
          <div v-for="(nestedValue, nestedKey) in value" :key="String(nestedKey)" class="flex items-start justify-between gap-4">
            <span class="text-slate-500">{{ nestedKey }}</span>
            <strong class="break-all text-right text-slate-900">{{ formatValue(nestedValue) }}</strong>
          </div>
          <div v-if="!Object.keys(value).length" class="text-xs text-slate-400">-</div>
        </div>
      </div>
      <div v-else class="flex items-start justify-between gap-4">
        <span class="text-slate-500">{{ key }}</span>
        <strong class="break-all text-right text-slate-900">{{ formatValue(value) }}</strong>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ data: Record<string, any> }>()

function isRecord(value: any) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function formatValue(value: any) {
  if (value === null || value === undefined || value === '') return '-'
  if (Array.isArray(value)) {
    return value.length
      ? value.map(item => typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item)).join('、')
      : '-'
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>
