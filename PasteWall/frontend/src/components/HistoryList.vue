<script setup lang="ts">
import { watch } from 'vue'
import { ElEmpty, ElMessage, ElPopconfirm } from 'element-plus'
import { Button } from '@/components/ui/button'
import { ApiError, deleteItem, imageUrl } from '@/api'
import { copyText, copyImageFile, canCopyImage } from '@/composables/useClipboard'
import { useLightbox } from '@/composables/useLightbox'
import { relTime, fmtSize } from '@/utils/time'
import type { Item } from '@/types'

const props = defineProps<{
  items: Item[]
  serverTime: number
}>()

const emit = defineEmits<{ changed: [] }>()

const lb = useLightbox()

// 入场动画:仅新出现的条目播一次
const seen = new Set<string>()
const fresh = new Set<string>()
watch(
  () => props.items,
  (list) => {
    fresh.clear()
    for (const it of list) if (!seen.has(it.id)) fresh.add(it.id)
    for (const it of list) seen.add(it.id)
  },
  { immediate: true },
)
function isNew(id: string) {
  return fresh.has(id)
}

async function onCopyText(item: Item) {
  const ok = await copyText(item.text ?? '')
  ok ? ElMessage.success('已复制') : ElMessage.error('复制失败,请手动选择文本后复制')
}

async function onCopyImage(item: Item) {
  if (!item.imageFile) return
  try {
    await copyImageFile(item.imageFile)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制图片失败,请改用下载')
  }
}

async function onDelete(item: Item) {
  try {
    await deleteItem(item.id)
    emit('changed')
  } catch (e: unknown) {
    if (e instanceof ApiError && e.status === 404) {
      emit('changed') // 已被其它设备删除,刷新即可
      return
    }
    ElMessage.error(`删除失败:${e instanceof Error ? e.message : e}`)
  }
}
</script>

<template>
  <section aria-labelledby="history-title">
    <div class="mb-3 flex items-baseline justify-between">
      <p id="history-title" class="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">历史记录</p>
      <span v-if="items.length" class="font-mono text-xs text-muted-foreground">共 {{ items.length }} 条</span>
    </div>

    <ElEmpty
      v-if="!items.length"
      description="还没有历史记录。"
      :image-size="72"
    />

    <ul v-else class="flex flex-col gap-3">
      <li v-for="item in items" :key="item.id" :class="isNew(item.id) ? 'item-new' : ''">
        <!-- 文字条目 -->
        <div
          v-if="item.type === 'text'"
          class="flex flex-wrap items-start gap-3 rounded-xl border border-border bg-card p-3.5 shadow-sm"
        >
          <div class="min-w-0 flex-1">
            <p class="break-pre-wrap">{{ item.text }}</p>
            <p class="mt-1.5 font-mono text-xs text-muted-foreground">{{ relTime(item.createdAt, serverTime) }}</p>
          </div>
          <div class="flex shrink-0 gap-2">
            <Button variant="outline" size="sm" class="text-accent-foreground" @click="onCopyText(item)">复制</Button>
            <ElPopconfirm
              title="删除这条文字?"
              confirm-button-text="删除"
              cancel-button-text="取消"
              :width="200"
              @confirm="onDelete(item)"
            >
              <template #reference>
                <Button variant="ghost" size="sm" class="text-destructive">删除</Button>
              </template>
            </ElPopconfirm>
          </div>
        </div>

        <!-- 图片条目 -->
        <div
          v-else
          class="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-3.5 shadow-sm"
        >
          <button
            type="button"
            class="h-[76px] w-[76px] shrink-0 cursor-pointer overflow-hidden rounded-lg border border-border p-0"
            :aria-label="'查看大图'"
            @click="lb.open(item)"
          >
            <img
              :src="item.imageFile ? imageUrl(item.imageFile) : ''"
              alt="图片"
              loading="lazy"
              class="h-full w-full object-cover transition-transform hover:scale-[1.04]"
            />
          </button>
          <div class="min-w-0 flex-1">
            <p class="font-mono text-xs text-muted-foreground">
              {{ relTime(item.createdAt, serverTime) }} · {{ fmtSize(item.size) }}
            </p>
          </div>
          <div class="flex shrink-0 gap-2">
            <Button
              v-if="canCopyImage"
              variant="outline"
              size="sm"
              class="text-accent-foreground"
              @click="onCopyImage(item)"
            >
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
            <ElPopconfirm
              title="删除这张图片?"
              confirm-button-text="删除"
              cancel-button-text="取消"
              :width="200"
              @confirm="onDelete(item)"
            >
              <template #reference>
                <Button variant="ghost" size="sm" class="text-destructive">删除</Button>
              </template>
            </ElPopconfirm>
          </div>
        </div>
      </li>
    </ul>
  </section>
</template>
