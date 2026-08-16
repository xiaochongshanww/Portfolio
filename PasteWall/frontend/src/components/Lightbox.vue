<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Button } from '@/components/ui/button'
import { useLightbox } from '@/composables/useLightbox'
import { copyImageFile, canCopyImage } from '@/composables/useClipboard'
import { imageUrl } from '@/api'
import { relTime, fmtSize } from '@/utils/time'
import type { Item } from '@/types'

const props = defineProps<{
  item: Item
  serverTime: number
}>()

const lb = useLightbox()

async function onCopy() {
  if (!props.item.imageFile) return
  try {
    await copyImageFile(props.item.imageFile)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制图片失败,请改用下载')
  }
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') lb.close()
}
onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-5">
    <div class="absolute inset-0 bg-[rgba(20,24,31,0.85)]" @click="lb.close()" />

    <div
      class="relative flex max-h-full max-w-[min(860px,100%)] flex-col overflow-hidden rounded-xl bg-card shadow-2xl"
      role="dialog"
      aria-modal="true"
      aria-label="查看图片"
    >
      <div class="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <span class="font-mono text-xs text-muted-foreground">
          图片 · {{ relTime(item.createdAt, serverTime) }} · {{ fmtSize(item.size) }}
        </span>
        <div class="flex shrink-0 gap-2">
          <Button v-if="canCopyImage" variant="outline" size="sm" class="text-accent-foreground" @click="onCopy">
            复制图片
          </Button>
          <a
            v-if="item.imageFile"
            :href="imageUrl(item.imageFile)"
            download
            class="inline-flex h-11 items-center whitespace-nowrap rounded-md border border-input bg-background px-3 text-xs transition-colors hover:bg-accent/15 hover:text-accent-foreground"
          >
            下载
          </a>
          <Button variant="ghost" size="sm" @click="lb.close()">关闭</Button>
        </div>
      </div>

      <img
        v-if="item.imageFile"
        :src="imageUrl(item.imageFile)"
        alt="大图"
        class="block max-h-[72vh] w-full max-w-full object-contain"
      />

      <p class="px-4 pb-3 pt-2 text-center text-xs text-muted-foreground">手机长按图片可保存</p>
    </div>
  </div>
</template>
