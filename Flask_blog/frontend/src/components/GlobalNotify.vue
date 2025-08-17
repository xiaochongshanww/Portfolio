<template>
  <div class="notify-wrap" v-if="queue.length">
    <div v-for="m in queue" :key="m.id" class="notice" :class="m.type">{{ m.text }}</div>
  </div>
</template>
<script setup>
import { useNotify } from '../composables/useNotify';
const { queue } = useNotify();
</script>
<style scoped>
.notify-wrap { position:fixed; top:12px; right:12px; display:flex; flex-direction:column; gap:8px; z-index:9999; }
.notice { background:#333; color:#fff; padding:8px 12px; border-radius:4px; font-size:14px; box-shadow:0 2px 6px rgba(0,0,0,.3); animation:fadeIn .25s; }
.notice.error { background:#d4380d; }
.notice.success { background:#2f8f2f; }
@keyframes fadeIn { from { opacity:0; transform:translateY(-4px);} to { opacity:1; transform:translateY(0);} }
</style>
