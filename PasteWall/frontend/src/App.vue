<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { usePolling } from '@/composables/usePolling'
import { useLightbox } from '@/composables/useLightbox'
import { fmtClock } from '@/utils/time'
import CurrentClipboard from '@/components/CurrentClipboard.vue'
import Composer from '@/components/Composer.vue'
import HistoryList from '@/components/HistoryList.vue'
import Lightbox from '@/components/Lightbox.vue'

const { items, serverTime, lastRefresh, load } = usePolling(5000)
const lb = useLightbox()

const latestText = computed(() => items.value.find((i) => i.type === 'text') ?? null)
const latestImage = computed(() => items.value.find((i) => i.type === 'image') ?? null)
const lightboxItem = computed(() => lb.current.value)
const refreshed = computed(() => (lastRefresh.value ? `刷新于 ${fmtClock(lastRefresh.value)}` : ''))
</script>

<template>
  <div class="mx-auto flex min-h-screen max-w-[720px] flex-col gap-5 px-4 pb-20 pt-7 sm:px-6">
    <header class="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="font-mono text-xl font-extrabold uppercase tracking-[0.22em]">PasteWall</h1>
        <p class="mt-1 text-sm text-muted-foreground">局域网共享剪贴板 · 贴一下,随时取</p>
      </div>
      <div class="flex items-center gap-3">
        <Badge v-if="refreshed" variant="outline" class="font-mono text-xs text-muted-foreground">
          {{ refreshed }}
        </Badge>
        <Button variant="outline" size="sm" @click="load">刷新</Button>
      </div>
    </header>

    <CurrentClipboard :latest-text="latestText" :latest-image="latestImage" />

    <Composer @published="load" />

    <HistoryList :items="items" :server-time="serverTime" @changed="load" />

    <Lightbox v-if="lightboxItem" :item="lightboxItem" :server-time="serverTime" />
  </div>
</template>
