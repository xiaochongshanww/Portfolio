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
        <!-- 登录态:写文章 CTA + 账号菜单(未登录不展示,登录/注册不入导航) -->
        <template v-if="userStore.isAuthenticated">
          <button type="button" class="write-btn" @click="go('/articles/new')">
            写文章
          </button>
          <div class="user-menu">
            <button
              type="button"
              class="avatar-btn"
              :aria-label="`账号菜单,${displayName}`"
              :aria-expanded="userMenuOpen"
              @click.stop="userMenuOpen = !userMenuOpen"
            >{{ initial }}</button>
            <div v-if="userMenuOpen" class="user-sheet">
              <div class="user-id">
                <b>{{ displayName }}</b>
                <small>{{ userStore.user?.email || '' }}</small>
              </div>
              <a href="/me/profile" class="user-link" @click.prevent="goMenu('/me/profile')">个人中心</a>
              <a href="/media" class="user-link" @click.prevent="goMenu('/media')">我的媒体库</a>
              <a
                v-if="userStore.canAccessAdmin"
                href="/admin"
                class="user-link"
                @click.prevent="goMenu('/admin')"
              >管理后台</a>
              <button type="button" class="user-link logout" @click="logout">退出登录</button>
            </div>
          </div>
        </template>
        <!-- 移动端导航入口(<720px 显示;桌面由 nav 承担) -->
        <button
          type="button"
          class="menu-toggle"
          aria-label="打开导航"
          :aria-expanded="menuOpen"
          @click="menuOpen = true"
        >
          <i /><i /><i />
        </button>
      </div>
    </div>

    <!-- 移动端导航抽屉 -->
    <Teleport to="body">
      <div v-if="menuOpen" class="menu-backdrop" @click.self="menuOpen = false">
        <nav class="menu-sheet" aria-label="移动端主导航">
          <div class="menu-head">
            <span>导航</span>
            <button type="button" class="menu-close" aria-label="关闭导航" @click="menuOpen = false">×</button>
          </div>
          <a
            v-for="item in navItems"
            :key="item.path"
            :href="item.path"
            class="menu-link"
            :class="{ active: isActive(item.path) }"
            @click.prevent="goMenu(item.path)"
          >{{ item.label }}</a>
        </nav>
      </div>
    </Teleport>
  </header>
</template>

<script>
/**
 * 公开站 Header(02 号规范第 1 节 / 01 号规范第 4 节)
 * sticky + 轻毛玻璃;当前导航仅文字变色;登录/注册不入导航。
 * P2-D2:搜索按钮触发全局 SearchOverlay;P2-E2:◐ 主题切换。
 * 登录态:写文章 CTA + 账号菜单(个人中心/媒体库/后台/退出),供创作工具页入公共壳。
 */
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSearchOverlay } from '../../composables/useSearchOverlay'
import { useTheme } from '../../composables/useTheme'
import { useUserStore } from '../../stores/user'

export default {
  name: 'PublicHeader',
  setup() {
    const route = useRoute()
    const router = useRouter()
    const { openOverlay } = useSearchOverlay()
    const { mode, cycleMode } = useTheme()
    const userStore = useUserStore()

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

    // 移动端导航抽屉
    const menuOpen = ref(false)

    /** @param {string} path */
    function goMenu(path) {
      menuOpen.value = false
      userMenuOpen.value = false
      go(path)
    }

    // 登录态账号菜单
    const userMenuOpen = ref(false)
    const displayName = computed(() => {
      /** @type {{ nickname?: string, email?: string }} */
      const u = userStore.user || {}
      return u.nickname || u.email || '用户'
    })
    const initial = computed(() => (displayName.value || '?').charAt(0).toUpperCase())

    /** 点击菜单外关闭 */
    function onDocClick() {
      userMenuOpen.value = false
    }
    /** 退出登录并回主页 */
    function logout() {
      userMenuOpen.value = false
      userStore.logout()
      router.push('/')
    }

    onMounted(() => document.addEventListener('click', onDocClick))
    onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

    const THEME_META = {
      light: { icon: '☀', label: '亮色' },
      dark: { icon: '☾', label: '暗色' },
      system: { icon: '◐', label: '跟随系统' },
    }
    const themeIcon = computed(() => THEME_META[mode.value].icon)
    const themeLabel = computed(() => THEME_META[mode.value].label)

    return {
      navItems, isActive, go, openSearch, themeIcon, themeLabel, cycleTheme: cycleMode,
      menuOpen, goMenu, userStore, userMenuOpen, displayName, initial, logout,
    }
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

/* 登录态:写文章 CTA + 账号菜单 */
.write-btn {
  height: 34px;
  padding: 0 14px;
  border: none;
  border-radius: 10px;
  background: var(--text);
  color: var(--bg);
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}
.write-btn:hover {
  opacity: 0.85;
}
.user-menu {
  position: relative;
}
.avatar-btn {
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.avatar-btn:hover {
  border-color: var(--line-strong);
}
.user-sheet {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 200px;
  padding: 6px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
  box-shadow: 0 8px 28px rgba(10, 10, 9, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 60;
}
.user-id {
  padding: 8px 10px 10px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 4px;
}
.user-id b {
  display: block;
  font-size: 13px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-id small {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-link {
  padding: 9px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  font-size: 13px;
  color: var(--muted);
  text-align: left;
  cursor: pointer;
  display: block;
}
.user-link:hover {
  color: var(--text);
  background: var(--surface-2);
}
.user-link.logout {
  border-top: 1px solid var(--line);
  margin-top: 4px;
  padding-top: 10px;
  padding-bottom: 10px;
  border-top-left-radius: 0;
  border-top-right-radius: 0;
  width: 100%;
}

@media (max-width: 720px) {
  .nav { display: none; }
  .header-inner { height: 60px; }
  .search-trigger kbd { display: none; }
  .search-trigger { padding: 0 12px; }
}

/* 移动端导航入口:桌面隐藏 */
.menu-toggle {
  display: none;
  width: 34px;
  height: 34px;
  padding: 0;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
  cursor: pointer;
}
.menu-toggle i {
  width: 14px;
  height: 1.5px;
  background: var(--muted);
  border-radius: 1px;
}
.menu-toggle:hover i { background: var(--text); }

@media (max-width: 719.98px) {
  .menu-toggle { display: inline-flex; }
}

/* 移动端导航抽屉 */
.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 250;
  background: rgba(10, 10, 9, 0.32);
  backdrop-filter: blur(3px);
}
.menu-sheet {
  position: absolute;
  top: 0;
  right: 0;
  width: min(300px, calc(100vw - 48px));
  height: 100%;
  padding: 14px;
  border-left: 1px solid var(--line);
  background: var(--surface);
  display: flex;
  flex-direction: column;
}
.menu-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px 14px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  color: var(--muted);
}
.menu-close {
  width: 32px;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-2);
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
}
.menu-link {
  padding: 14px 10px;
  border-bottom: 1px solid var(--line);
  font-size: 16px;
  color: var(--muted);
}
.menu-link.active,
.menu-link:hover {
  color: var(--text);
}
.menu-link.active {
  font-weight: 650;
}
@media (max-width: 480px) {
  .shell { padding-left: 18px; padding-right: 18px; }
}
</style>
