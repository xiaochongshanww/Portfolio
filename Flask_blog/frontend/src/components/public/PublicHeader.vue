<template>
  <header class="site-header">
    <div class="shell header-inner">
      <a href="/" class="brand" @click.prevent="go('/')">
        <span class="brand-mark">山</span>
        <span class="brand-name">小重山</span>
      </a>
      <nav class="nav" aria-label="主导航">
        <a
          v-for="item in navItems"
          :key="item.path"
          :href="item.path"
          class="nav-link"
          :class="{ active: isActive(item.path) }"
          @click.prevent="go(item.path)"
        >{{ item.label }}</a>
      </nav>
      <div class="header-actions">
        <button
          type="button"
          class="search-trigger"
          aria-label="搜索"
          @click="openSearch"
        >
          搜索 <kbd>⌘K</kbd>
        </button>
        <button
          type="button"
          class="theme-toggle"
          :aria-label="`切换主题,当前${themeLabel}`"
          :title="`主题:${themeLabel}`"
          @click="cycleTheme"
        >
          {{ themeIcon }}
        </button>
      </div>
    </div>
  </header>
</template>

<script>
/**
 * 公开站 Header(02 号规范第 1 节 / 01 号规范第 4 节)
 * sticky + 轻毛玻璃;当前导航仅文字变色;登录/注册不入导航。
 * P2-D2:搜索按钮触发全局 SearchOverlay;P2-E2:◐ 主题切换。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSearchOverlay } from '../../composables/useSearchOverlay'
import { useTheme } from '../../composables/useTheme'

export default {
  name: 'PublicHeader',
  setup() {
    const route = useRoute()
    const router = useRouter()
    const { openOverlay } = useSearchOverlay()
    const { mode, cycleMode } = useTheme()

    const navItems = [
      { label: '文章', path: '/' },
      { label: '项目', path: '/projects' },
      { label: '专题', path: '/topics' },
      { label: '归档', path: '/archive' },
      { label: '关于', path: '/about' },
    ]

    const currentPath = computed(() => route.path)

    /** @param {string} path */
    function isActive(path) {
      if (path === '/') return currentPath.value === '/'
      return currentPath.value.startsWith(path)
    }

    /** @param {string} path */
    function go(path) {
      router.push(path)
    }

    /** @param {MouseEvent} e 搜索按钮点击,触发元素用于焦点归还 */
    function openSearch(e) {
      openOverlay(e.currentTarget instanceof HTMLElement ? e.currentTarget : null)
    }

    const THEME_META = {
      light: { icon: '☀', label: '亮色' },
      dark: { icon: '☾', label: '暗色' },
      system: { icon: '◐', label: '跟随系统' },
    }
    const themeIcon = computed(() => THEME_META[mode.value].icon)
    const themeLabel = computed(() => THEME_META[mode.value].label)

    return { navItems, isActive, go, openSearch, themeIcon, themeLabel, cycleTheme: cycleMode }
  },
}
</script>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: color-mix(in srgb, var(--bg) 93%, transparent);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid color-mix(in srgb, var(--line) 85%, transparent);
}
.header-inner {
  height: 66px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 760;
  letter-spacing: -0.03em;
}
.brand-mark {
  width: 29px;
  height: 29px;
  border-radius: 9px;
  background: var(--text);
  color: var(--bg);
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
}
.brand-name {
  font-size: 16px;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.nav {
  display: flex;
  gap: 23px;
}
.nav-link {
  font-size: 14px;
  color: var(--muted);
  padding: 6px 2px;
}
.nav-link:hover,
.nav-link.active {
  color: var(--text);
}
.search-trigger {
  height: 34px;
  padding: 0 11px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.search-trigger:hover {
  color: var(--text);
  border-color: var(--line-strong);
}
.search-trigger kbd {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 10px;
}
/* 主题切换(P2-E2):移动端搜索按钮保留,切换器常驻 */
.theme-toggle {
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
  color: var(--muted);
  font-size: 14px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.theme-toggle:hover {
  color: var(--text);
  border-color: var(--line-strong);
}

@media (max-width: 720px) {
  .nav { display: none; }
  .header-inner { height: 60px; }
  .search-trigger kbd { display: none; }
  .search-trigger { padding: 0 12px; }
}
@media (max-width: 480px) {
  .shell { padding-left: 18px; padding-right: 18px; }
}
</style>
