import { computed } from 'vue'
import { imageUrl } from '@/api'

/** 局域网 HTTP 是非安全上下文:图片复制能力需检测;不支持时隐藏,退化为下载/长按保存 */
export const canCopyImage = computed(() => {
  const win = window as unknown as Record<string, unknown>
  const nav = navigator as unknown as { clipboard?: { write?: unknown } }
  return !!(nav.clipboard?.write && 'ClipboardItem' in win && window.isSecureContext)
})

function legacyCopy(text: string): boolean {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.readOnly = true
  ta.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0;'
  document.body.appendChild(ta)
  ta.select()
  ta.setSelectionRange(0, ta.value.length)
  let ok = false
  try {
    ok = document.execCommand('copy')
  } finally {
    ta.remove()
  }
  return ok
}

export async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      /* 落到旧路径 */
    }
  }
  return legacyCopy(text)
}

export async function copyImageFile(file: string): Promise<void> {
  const res = await fetch(imageUrl(file))
  if (!res.ok) throw new Error('加载图片失败')
  const blob = await res.blob()
  const type = blob.type || 'image/png'
  await navigator.clipboard.write([new ClipboardItem({ [type]: blob })])
}
