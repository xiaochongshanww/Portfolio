import { ref, watch } from 'vue'
import type { Item } from '@/types'

/** 模块级共享的灯箱状态:任一组件打开,App 统一渲染 */
const current = ref<Item | null>(null)

watch(current, (item) => {
  document.body.style.overflow = item ? 'hidden' : ''
})

export function useLightbox() {
  return {
    current,
    open(item: Item) {
      current.value = item
    },
    close() {
      current.value = null
    },
  }
}
