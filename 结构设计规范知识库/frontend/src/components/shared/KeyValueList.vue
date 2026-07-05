<template>
  <div class="space-y-2 text-sm">
    <div v-for="(value, key) in data" :key="String(key)" class="flex items-start justify-between gap-4">
      <span class="text-slate-500">{{ key }}</span>
      <strong class="text-right text-slate-900">{{ value }}</strong>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ data: Record<string, any> }>()
</script>
