<template>
  <div class="panel p-4">
    <div class="text-xs text-slate-500">{{ label }}</div>
    <div class="mt-2 text-2xl font-semibold text-slate-950">{{ value }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string, value: string | number }>()
</script>
