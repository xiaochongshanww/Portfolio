<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { postText, postImage, IMAGE_TYPES } from '@/api'

const emit = defineEmits<{ published: [] }>()

const text = ref('')
const publishing = ref(false)
const uploading = ref(false)
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement>()

const MAX_CLIENT_BYTES = 40 * 1024 * 1024

function publishText(value?: string) {
  const content = value ?? text.value
  if (!content.trim() || publishing.value) return
  publishing.value = true
  postText(content)
    .then(() => {
      if (value === undefined) text.value = ''
      emit('published')
      if (value !== undefined) ElMessage.success('已发布')
    })
    .catch((e: unknown) => {
      // 自动发布失败:把粘贴内容放回输入框,便于手动重试
      if (value !== undefined) text.value = value
      ElMessage.error(`发布失败:${e instanceof Error ? e.message : e}`)
    })
    .finally(() => {
      publishing.value = false
    })
}

// 向输入框粘贴纯文字 → 自动发布(与图片粘贴行为一致,不再需要点"发布")
function onTextareaPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (items) {
    for (const it of items) {
      // 有图片:阻止浏览器原生"插入到文本框"路径,避免其消耗剪贴板字节;
      // 事件继续冒泡交给文档级处理器发布图片
      if (it.type.startsWith('image/')) {
        e.preventDefault()
        return
      }
    }
  }
  const pasted = e.clipboardData?.getData('text') ?? ''
  if (!pasted.trim()) return
  e.preventDefault() // 不写入输入框,直接发布
  publishText(pasted)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    publishText()
  }
}

function publishImageFile(file: File) {
  if (!(IMAGE_TYPES as readonly string[]).includes(file.type)) {
    ElMessage.error('仅支持 PNG / JPEG / GIF / WebP 图片')
    return
  }
  if (file.size > MAX_CLIENT_BYTES) ElMessage.warning('图片较大,可能超过服务端 64MB 上传上限')
  if (uploading.value) return
  uploading.value = true

  const reader = new FileReader()
  reader.onload = () => {
    const dataBase64 = String(reader.result).split(',')[1] || ''
    postImage(file.type, dataBase64)
      .then(() => emit('published'))
      .catch((e: unknown) => ElMessage.error(`发布失败:${e instanceof Error ? e.message : e}`))
      .finally(() => {
        uploading.value = false
      })
  }
  reader.onerror = () => {
    uploading.value = false
    ElMessage.error('读取文件失败')
  }
  reader.readAsDataURL(file)
}

// 图片粘贴:不劫持文字粘贴(文字粘贴由 textarea 默认处理)
function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const it of items) {
    if (it.type.startsWith('image/')) {
      e.preventDefault()
      const f = it.getAsFile()
      if (f) publishImageFile(f)
      return
    }
  }
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f && f.type.startsWith('image/')) publishImageFile(f)
}

function preventDefault(e: Event) {
  e.preventDefault()
}

function pickFile() {
  if (!uploading.value) fileInput.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) publishImageFile(input.files[0])
  input.value = ''
}

onMounted(() => {
  document.addEventListener('paste', onPaste)
  document.addEventListener('dragover', preventDefault)
  document.addEventListener('drop', preventDefault)
})
onUnmounted(() => {
  document.removeEventListener('paste', onPaste)
  document.removeEventListener('dragover', preventDefault)
  document.removeEventListener('drop', preventDefault)
})
</script>

<template>
  <section class="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm">
    <Textarea
      v-model="text"
      placeholder="粘贴文字将自动发布;输入文字请按 Ctrl+Enter"
      :disabled="publishing"
      @keydown="onKeydown"
      @paste="onTextareaPaste"
    />

    <div class="flex flex-col gap-3 sm:flex-row">
      <Button :disabled="!text.trim() || publishing" @click="publishText">
        {{ publishing ? '发布中…' : '发布' }}
      </Button>

      <div
        role="button"
        tabindex="0"
        class="flex min-h-11 flex-1 cursor-pointer items-center justify-center gap-2.5 rounded-md border-[1.5px] border-dashed border-input px-3 py-3 text-center text-sm text-muted-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        :class="dragOver ? 'border-accent bg-accent/10 text-foreground' : 'hover:border-accent hover:bg-accent/10 hover:text-foreground'"
        :aria-label="'上传图片'"
        @click="pickFile"
        @keydown.enter="pickFile"
        @keydown.space.prevent="pickFile"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop="onDrop"
      >
        <svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 16V4m0 0L7 9m5-5 5 5"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          />
        </svg>
        <span>
          {{ uploading ? '上传中…' : 'Ctrl+V 粘贴截图 · 拖拽图片到此处 · 或点此选择' }}
        </span>
      </div>
    </div>

    <input
      ref="fileInput"
      type="file"
      accept="image/png,image/jpeg,image/gif,image/webp"
      class="hidden"
      @change="onFileChange"
    />
  </section>
</template>
