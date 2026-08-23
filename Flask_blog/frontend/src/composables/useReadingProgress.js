/**
 * 阅读进度(03 号规范第 22 节):单例 progress state,
 * 顶部进度条 / Reading Rail / 移动端 FAB 三处共享同一数值。
 */
import { ref, onMounted, onUnmounted } from 'vue'

/** 模块级单例:同一页面多处消费保持同步 */
const progress = ref(0)

/** 当前是否已有消费者挂载了 scroll 监听 */
let listeners = 0
/** @type {(() => void) | null} */
let detachScroll = null

function updateProgress() {
  const doc = document.documentElement
  const max = Math.max(1, doc.scrollHeight - doc.clientHeight)
  const pct = Math.max(0, Math.min(100, (window.scrollY / max) * 100))
  progress.value = Math.round(pct)
}

/**
 * 在组件中使用:const { progress } = useReadingProgress()
 * 组件卸载时自动清理监听(引用计数)。
 */
export function useReadingProgress() {
  let localDetach = null

  onMounted(() => {
    listeners += 1
    if (!detachScroll) {
      window.addEventListener('scroll', updateProgress, { passive: true })
      window.addEventListener('resize', updateProgress)
      detachScroll = () => {
        window.removeEventListener('scroll', updateProgress)
        window.removeEventListener('resize', updateProgress)
      }
    }
    updateProgress()
    localDetach = () => {
      listeners -= 1
      if (listeners <= 0 && detachScroll) {
        detachScroll()
        detachScroll = null
        listeners = 0
      }
    }
  })

  onUnmounted(() => {
    if (localDetach) localDetach()
  })

  return { progress }
}
