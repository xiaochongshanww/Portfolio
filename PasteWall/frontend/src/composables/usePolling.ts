import { onMounted, onUnmounted, ref } from 'vue'
import { fetchItems } from '@/api'
import type { Item } from '@/types'

/** 5 秒轮询 + 手动刷新 + 窗口聚焦/回到前台即刷新;loading 防重叠 */
export function usePolling(intervalMs = 5000) {
  const items = ref<Item[]>([])
  const serverTime = ref(Date.now())
  const lastRefresh = ref<Date | null>(null)
  const loading = ref(false)
  let timer: number | undefined

  async function load(): Promise<void> {
    if (loading.value) return
    loading.value = true
    try {
      const data = await fetchItems()
      items.value = data.items
      serverTime.value = data.serverTime
      lastRefresh.value = new Date()
    } catch {
      // 网络失败时保留上次内容,不做每 5 秒打扰
    } finally {
      loading.value = false
    }
  }

  function onVisibility() {
    if (!document.hidden) load()
  }
  function onFocus() {
    load()
  }

  onMounted(() => {
    load()
    timer = window.setInterval(load, intervalMs)
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('focus', onFocus)
  })
  onUnmounted(() => {
    window.clearInterval(timer)
    document.removeEventListener('visibilitychange', onVisibility)
    window.removeEventListener('focus', onFocus)
  })

  return { items, serverTime, lastRefresh, loading, load }
}
