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
        <button type="button" class="search-trigger" aria-label="搜索">
          搜索 <kbd>⌘K</kbd>
        </button>
      </div>
    </div>
  </header>
</template>

<script>
/**
 * 公开站 Header(02 号规范第 1 节 / 01 号规范第 4 节)
 * sticky + 轻毛玻璃;当前导航仅文字变色;登录/注册不入导航。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export default {
  name: 'PublicHeader',
  setup() {
    const route = useRoute()
    const router = useRouter()

    const navItems = [
      { label: '文章', path: '/' },
      { label: '项目', path: '/projects' },
      { label: '专题', path: '/topics' },
      { label: '归档', path: '/archive' },
      { label: '关于', path: '/about' },
    ]

    const currentPath = computed(() => route.path)

    function isActive(path) {
      if (path === '/') return currentPath.value === '/'
      return currentPath.value.startsWith(path)
    }

    function go(path) {
      router.push(path)
    }

    return { navItems, isActive, go }
  },
}
</script>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: rgba(247, 247, 245, 0.93);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(227, 227, 223, 0.85);
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

@media (max-width: 720px) {
  .nav { display: none; }
  .header-inner { height: 60px; }
}
@media (max-width: 480px) {
  .shell { padding-left: 18px; padding-right: 18px; }
}
</style>
