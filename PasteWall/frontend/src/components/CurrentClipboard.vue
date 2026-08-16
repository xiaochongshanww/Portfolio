<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { Button } from '@/components/ui/button'
import { copyText, copyImageFile, canCopyImage } from '@/composables/useClipboard'
import { useLightbox } from '@/composables/useLightbox'
import { imageUrl } from '@/api'
import type { Item } from '@/types'

const props = defineProps<{
  latestText: Item | null
  latestImage: Item | null
}>()

const lb = useLightbox()

async function onCopyText() {
  if (!props.latestText?.text) return
  const ok = await copyText(props.latestText.text)
  ok ? ElMessage.success('已复制') : ElMessage.error('复制失败,请手动选择文本后复制')
}

async function onCopyImage() {
  if (!props.latestImage?.imageFile) return
  try {
    await copyImageFile(props.latestImage.imageFile)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制图片失败,请改用下载')
  }
}
</script>

<template>
  <section class="relative rounded-xl border border-border bg-card shadow-sm">
    <!-- 金属夹:签名元素 -->
    <svg
      class="absolute top-[-14px] left-1/2 -translate-x-1/2 z-10 h-7 w-24 drop-shadow-[0_2px_3px_rgba(31,39,51,0.25)]"
      viewBox="0 0 96 28"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="clipMetal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#eef1f4" />
          <stop offset="1" stop-color="#b3bcc7" />
        </linearGradient>
      </defs>
      <path
        d="M10 4 h76 a6 6 0 0 1 6 6 v6 a6 6 0 0 1 -6 6 h-76 a6 6 0 0 1 -6 -6 v-6 a6 6 0 0 1 6 -6 z"
        fill="url(#clipMetal)"
        stroke="#87919e"
        stroke-width="1.5"
      />
      <rect x="2" y="18" width="92" height="5" rx="2.5" fill="#aeb7c2" stroke="#87919e" stroke-width="1" />
      <circle cx="48" cy="11" r="3.5" fill="#6b7684" />
      <circle cx="48" cy="11" r="1.6" fill="#d8dde3" />
    </svg>

    <div class="p-5 pt-7">
      <p class="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">当前剪贴板</p>

      <div class="mt-3 grid gap-3 md:grid-cols-2">
        <!-- 最近文字 -->
        <div class="flex min-w-0 flex-col gap-3 rounded-lg border border-border bg-muted/40 p-3">
          <div class="flex items-center justify-between gap-2">
            <span class="whitespace-nowrap text-xs text-muted-foreground">最近文字</span>
            <Button
              variant="outline"
              size="sm"
              class="shrink-0 text-accent-foreground"
              :disabled="!latestText"
              @click="onCopyText"
            >
              复制
            </Button>
          </div>
          <p v-if="latestText" class="break-pre-wrap text-[15px]">{{ latestText.text }}</p>
          <p v-else class="text-sm text-muted-foreground">共享板还是空的,从下方贴一段文字或一张图片,其他设备就能看到了。</p>
        </div>

        <!-- 最近图片 -->
        <div class="flex min-w-0 flex-col gap-3 rounded-lg border border-border bg-muted/40 p-3">
          <div class="flex items-center justify-between gap-2">
            <span class="whitespace-nowrap text-xs text-muted-foreground">最近图片</span>
            <div v-if="latestImage" class="flex shrink-0 gap-2">
              <Button v-if="canCopyImage" variant="outline" size="sm" class="text-accent-foreground" @click="onCopyImage">
                复制图片
              </Button>
              <a
                :href="latestImage && imageUrl(latestImage.imageFile!)"
                download
                class="inline-flex h-11 items-center whitespace-nowrap rounded-md border border-input bg-background px-3 text-xs transition-colors hover:bg-accent/15 hover:text-accent-foreground"
              >
                下载
              </a>
            </div>
          </div>
          <button
            v-if="latestImage"
            type="button"
            class="h-[132px] w-full cursor-pointer overflow-hidden rounded-md border border-border p-0"
            :aria-label="'查看最近图片'"
            @click="lb.open(latestImage)"
          >
            <img :src="latestImage.imageFile ? imageUrl(latestImage.imageFile) : ''" alt="最近图片" class="h-full w-full object-cover" />
          </button>
          <p v-else class="text-sm text-muted-foreground">还没有图片,截图后 Ctrl+V 贴上来。</p>
        </div>
      </div>
    </div>
  </section>
</template>
