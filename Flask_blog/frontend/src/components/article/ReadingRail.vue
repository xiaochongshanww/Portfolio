<template>
  <div>
    <!-- 桌面悬浮 Rail(≥1280px):fixed 定位,不占布局,不推动正文 -->
    <aside class="reading-rail" :class="{ visible: railVisible }">
      <div class="rail">
        <div class="rail-head">
          <span>本文目录</span>
          <span>{{ progress }}%</span>
        </div>
        <a
          v-for="item in toc"
          :key="item.anchor"
          :href="'#' + item.anchor"
          class="rail-link"
          :class="{ active: item.anchor === currentAnchor }"
        >{{ item.text }}</a>
        <div class="rail-sep" />
        <div class="rail-actions">
          <button type="button" @click="copyLink">复制链接</button>
          <button type="button" @click="toTop">回到顶部</button>
        </div>
      </div>
    </aside>

    <!-- 窄屏 FAB + Drawer(<1280px) -->
    <button
      v-if="!railVisible || true"
      type="button"
      class="toc-fab"
      @click="drawerOpen = true"
    >
      目录 <span class="fab-pct">{{ progress }}%</span>
    </button>

    <Teleport to="body">
      <div v-if="drawerOpen" class="toc-backdrop" @click.self="drawerOpen = false">
        <div class="toc-sheet" role="dialog" aria-label="本文目录">
          <div class="sheet-head">
            <b>本文目录</b>
            <span>已阅读 {{ progress }}%</span>
            <button type="button" class="sheet-close" aria-label="关闭目录" @click="drawerOpen = false">×</button>
          </div>
          <div class="sheet-list">
            <a
              v-for="(item, i) in toc"
              :key="item.anchor"
              :href="'#' + item.anchor"
              @click="drawerOpen = false"
            >
              <span>{{ item.text }}</span>
              <small>{{ String(i + 1).padStart(2, '0') }}</small>
            </a>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useReadingProgress } from '../../composables/useReadingProgress'

export default {
  name: 'ReadingRail',
  props: {
    /** [{ anchor: string, text: string }] 由 H2 生成的目录 */
    toc: {
      type: /** @type {import('vue').PropType<Array<{anchor:string,text:string}>>} */ (Array),
      default: () => [],
    },
  },
  setup() {
    const { progress } = useReadingProgress()
    const railVisible = ref(false)
    const currentAnchor = ref('')
    const drawerOpen = ref(false)

    let observer = null

    /** @param {KeyboardEvent} e */
    function onKeydown(e) {
      if (e.key === 'Escape') drawerOpen.value = false
    }

    function updateRailVisibility() {
      // Lead visual 滚出视口后显示(简化:滚过 400px 即出现)
      railVisible.value = window.scrollY > 400
    }

    onMounted(() => {
      window.addEventListener('scroll', updateRailVisibility, { passive: true })
      document.addEventListener('keydown', onKeydown)
      updateRailVisibility()

      // 当前章节高亮:观察所有 heading 锚点(环境无 IntersectionObserver 时跳过,如 jsdom)
      if (typeof IntersectionObserver === 'undefined') return
      observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              currentAnchor.value = entry.target.id
            }
          }
        },
        { rootMargin: '-90px 0px -70% 0px' },
      )
      // toc anchors 在 mounted 后由父组件渲染完成,延迟挂载观察
      setTimeout(() => {
        document.querySelectorAll('[data-toc-anchor]').forEach((el) => observer?.observe(el))
      }, 100)
    })

    onUnmounted(() => {
      window.removeEventListener('scroll', updateRailVisibility)
      document.removeEventListener('keydown', onKeydown)
      observer?.disconnect()
    })

    async function copyLink() {
      try { await navigator.clipboard.writeText(window.location.href) } catch (e) { /* 静默 */ }
    }

    function toTop() {
      window.scrollTo({ top: 0 })
    }

    return { progress, railVisible, currentAnchor, drawerOpen, copyLink, toTop }
  },
}
</script>

<style scoped>
/* 03 号规范第 19/20 节:页面级浮层,fixed 定位;存在与否不影响正文 x 坐标 */
.reading-rail {
  position: fixed;
  top: 94px;
  right: 26px;
  width: 188px;
  z-index: 30;
  opacity: 0;
  transform: translateY(8px);
  pointer-events: none;
  transition: opacity var(--transition), transform var(--transition);
}
.reading-rail.visible {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}
@media (prefers-reduced-motion: reduce) {
  .reading-rail { transition: none; }
}

.rail {
  padding: 14px 12px 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
  box-shadow: 0 14px 36px rgba(18, 18, 16, 0.07);
}
.rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--muted);
}
.rail-link {
  display: block;
  padding: 7px 8px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rail-link:hover {
  background: var(--surface-2);
  color: var(--text);
}
.rail-link.active {
  background: var(--signal-soft);
  color: var(--signal-ink);
  font-weight: 650;
}
.rail-sep {
  height: 1px;
  background: var(--line);
  margin: 10px 0;
}
.rail-actions {
  display: flex;
  gap: 8px;
}
.rail-actions button {
  flex: 1;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--muted);
  font-size: 11px;
  cursor: pointer;
}
.rail-actions button:hover {
  color: var(--text);
  border-color: var(--line-strong);
}

/* 窄屏 FAB */
.toc-fab {
  display: none;
  position: fixed;
  right: 18px;
  bottom: 20px;
  z-index: 50;
  height: 40px;
  padding: 0 13px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 10px 28px rgba(18, 18, 16, 0.12);
  align-items: center;
  gap: 7px;
  font-size: 13px;
  cursor: pointer;
}
.fab-pct {
  color: var(--muted);
  font-size: 11px;
}

@media (max-width: 1279.98px) {
  .reading-rail { display: none; }
  .toc-fab { display: flex; }
}

/* Drawer */
.toc-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: rgba(10, 10, 9, 0.32);
  backdrop-filter: blur(3px);
}
.toc-sheet {
  position: absolute;
  right: 16px;
  bottom: 16px;
  width: min(360px, calc(100vw - 32px));
  max-height: 70vh;
  overflow: auto;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
  box-shadow: 0 26px 70px rgba(0, 0, 0, 0.2);
}
.sheet-head {
  padding-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--line);
}
.sheet-head b { font-size: 15px; }
.sheet-head span {
  flex: 1;
  text-align: right;
  font-size: 12px;
  color: var(--muted);
}
.sheet-close {
  width: 32px;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-2);
  color: var(--muted);
  cursor: pointer;
}
.sheet-list { padding-top: 8px; }
.sheet-list a {
  padding: 10px 8px;
  border-radius: 9px;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  color: var(--muted);
  font-size: 14px;
}
.sheet-list a.active,
.sheet-list a:hover {
  background: var(--surface-2);
  color: var(--text);
}
.sheet-list small { font-size: 11px; color: var(--muted); }
</style>
