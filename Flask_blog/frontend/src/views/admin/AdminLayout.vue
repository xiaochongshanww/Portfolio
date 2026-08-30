<template>
  <div class="admin-scope app-shell">
    <!-- Sidebar(04 §5:224px,五分组,底部账号) -->
    <aside class="sidebar" :class="{ open: mobileOpen }">
      <div class="side-brand">
        <span class="brand-mark">山</span>
        <span class="brand-name">小重山 CMS</span>
      </div>

      <div class="side-scroll">
        <div v-for="group in visibleGroups" :key="group.label" class="nav-group">
          <div class="nav-label">{{ group.label }}</div>
          <RouterLink
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
            @click="mobileOpen = false"
          >
            <el-icon class="nav-icon" :size="15"><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
            <span v-if="item.count != null" class="nav-count">{{ item.count }}</span>
          </RouterLink>
        </div>
      </div>

      <div class="side-footer">
        <el-dropdown trigger="click" placement="top-start" width="200">
          <button type="button" class="account">
            <span class="avatar">{{ accountInitial }}</span>
            <span class="account-copy">
              <span class="account-name">{{ accountName }}</span>
              <span class="account-role">{{ roleText }}</span>
            </span>
            <span class="account-caret">⌄</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item data-testid="admin-logout" @click="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <!-- 移动端遮罩 -->
    <div v-if="mobileOpen" class="mobile-backdrop" @click="mobileOpen = false" />

    <!-- Main -->
    <div class="main">
      <!-- Topbar(04 §6:面包屑 + 返回网站,不放业务动作) -->
      <header class="topbar">
        <div class="topbar-left">
          <button type="button" class="menu-btn" aria-label="打开导航" @click="mobileOpen = true">
            <i /><i /><i />
          </button>
          <nav class="breadcrumb" aria-label="面包屑">
            <template v-for="(c, i) in breadcrumbs" :key="i">
              <span v-if="i > 0" class="crumb-sep">/</span>
              <RouterLink v-if="c.to" :to="c.to" class="crumb-link">{{ c.text }}</RouterLink>
              <b v-else>{{ c.text }}</b>
            </template>
          </nav>
        </div>
        <div class="top-actions">
          <RouterLink to="/" class="top-btn">↗ 返回网站</RouterLink>
        </div>
      </header>

      <!-- Workspace(04 V2 §5):padding 属于壳,内容区限宽 -->
      <main class="workspace">
        <div class="content">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Admin Shell(04 号规范 §4-§7 / 05 号规范 §2)
 * - Sidebar:224px 五分组 IA(工作台/内容/组织/资源/系统),账号在底部;
 * - Topbar:面包屑 + 返回网站,不放业务动作(业务动作属于 PageHeader);
 * - 视觉全部来自 style/admin.css 的 --adm-* tokens,无渐变无 Glow。
 */
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  DataBoard, Document, View, ChatLineRound, Collection, PriceTag, Box,
  Picture, User, Lock, Memo, Setting,
} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '../../stores/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

/** 新 IA(04 §5.3);旧页面(备份/恢复/性能)归入系统分组,URL 不变 */
interface NavItem {
  label: string
  path: string
  icon: unknown
  roles?: string[]
  count?: number
}
interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: '工作台',
    items: [{ label: '仪表盘', path: '/admin', icon: DataBoard }],
  },
  {
    label: '内容',
    items: [
      { label: '文章', path: '/admin/articles', icon: Document, roles: ['author', 'editor', 'admin'] },
      { label: '审核', path: '/admin/articles/review', icon: View, roles: ['editor', 'admin'] },
      { label: '评论', path: '/admin/comments', icon: ChatLineRound, roles: ['editor', 'admin'] },
    ],
  },
  {
    label: '组织',
    items: [
      { label: '专题', path: '/admin/categories', icon: Collection, roles: ['editor', 'admin'] },
      { label: '标签', path: '/admin/tags', icon: PriceTag, roles: ['editor', 'admin'] },
      { label: '项目', path: '/admin/projects', icon: Box, roles: ['editor', 'admin'] },
    ],
  },
  {
    label: '资源',
    items: [{ label: '媒体', path: '/admin/media', icon: Picture, roles: ['author', 'editor', 'admin'] }],
  },
  {
    label: '系统',
    items: [
      { label: '用户', path: '/admin/users', icon: User, roles: ['admin'] },
      { label: '安全', path: '/admin/security', icon: Lock, roles: ['editor', 'admin'] },
      { label: '日志', path: '/admin/logs', icon: Memo, roles: ['editor', 'admin'] },
      { label: '设置', path: '/admin/settings/general', icon: Setting, roles: ['admin'] },
    ],
  },
];

const role = computed(() => userStore.user?.role || '');

const visibleGroups = computed(() =>
  NAV_GROUPS.map((g) => ({
    label: g.label,
    items: g.items.filter(
      (item) => !item.roles || item.roles.includes(role.value),
    ),
  })).filter((g) => g.items.length > 0),
);

/** 命中规则:精确路径,或前缀命中;审核子页高亮"审核"而非"文章" */
function isActive(path: string): boolean {
  if (path === '/admin') return route.path === '/admin';
  if (path === '/admin/articles' && route.path.startsWith('/admin/articles/review')) {
    return false;
  }
  return route.path === path || route.path.startsWith(path + '/');
}

/** 面包屑:分组名 / 页面名(当前路由命中的 nav item) */
const breadcrumbs = computed(() => {
  for (const g of NAV_GROUPS) {
    for (const item of g.items) {
      if (isActive(item.path)) {
        return g.label === item.label
          ? [{ text: item.label }]
          : [{ text: g.label }, { text: item.label }];
      }
    }
  }
  // 编辑/审核等子页:前缀命中父级后补当前路径段
  if (route.path.includes('/articles/review')) {
    return [{ text: '内容' }, { text: '文章', to: '/admin/articles' }, { text: '文章审核' }];
  }
  if (route.path.includes('/articles/') && route.path !== '/admin/articles') {
    return [{ text: '内容' }, { text: '文章', to: '/admin/articles' }, { text: '编辑文章' }];
  }
  return [{ text: '工作台' }, { text: '仪表盘', to: '/admin' }];
});

const accountName = computed(() => userStore.user?.email || userStore.user?.nickname || '');
const accountInitial = computed(() => (accountName.value || 'U').slice(0, 1).toUpperCase());
const roleText = computed(() => {
  switch (role.value) {
    case 'admin': return '管理员';
    case 'editor': return '编辑';
    case 'author': return '作者';
    default: return '用户';
  }
});

async function logout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    await userStore.logout();
    ElMessage.success('已退出登录');
    router.push('/login');
  } catch {
    // 用户取消
  }
}

// <720px Sidebar 抽屉(04 §27)
const mobileOpen = ref(false);
let mq: MediaQueryList | null = null;
function onMqChange(e: MediaQueryListEvent) {
  if (e.matches) mobileOpen.value = false;
}
onMounted(() => {
  mq = window.matchMedia('(max-width: 719.98px)');
  mq.addEventListener('change', onMqChange);
});
onUnmounted(() => mq?.removeEventListener('change', onMqChange));
</script>

<style scoped>
/* 04 V2 §1/§4:应用壳占满 viewport,Sidebar 贴屏幕最左,Main 占全部剩余宽度 */
.app-shell {
  width: 100vw;
  min-height: 100vh;
  display: grid;
  grid-template-columns: var(--adm-sidebar-w) minmax(0, 1fr);
  background: var(--adm-bg);
  color: var(--adm-text);
}

/* ── Sidebar ─────────────────────────────── */
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  background: var(--adm-surface);
  border-right: 1px solid var(--adm-border);
  display: flex;
  flex-direction: column;
}
.side-brand {
  height: var(--adm-header-h);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  border-bottom: 1px solid var(--adm-border);
  font-weight: 760;
  letter-spacing: -0.02em;
  font-size: 14px;
  flex-shrink: 0;
}
.brand-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--adm-text);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
}
.side-scroll {
  padding: 14px 10px 16px;
  overflow: auto;
  flex: 1;
}
.nav-group {
  margin-bottom: 18px;
}
.nav-label {
  padding: 0 9px 7px;
  font-size: 11px;
  font-weight: 650;
  color: var(--adm-muted-light);
  letter-spacing: 0.02em;
}
.nav-item {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  margin: 2px 0;
  border-radius: 8px;
  color: var(--adm-text-2);
  font-size: 13px;
}
.nav-item:hover {
  background: #f7f7f8;
}
.nav-item.active {
  background: var(--adm-primary-soft);
  color: var(--adm-primary);
  font-weight: 650;
}
.nav-icon {
  width: 17px;
  display: inline-flex;
  justify-content: center;
}
.nav-count {
  margin-left: auto;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #f4f4f5;
  color: var(--adm-muted);
  font-size: 10px;
}
.nav-item.active .nav-count {
  background: #fff;
  color: var(--adm-primary);
}
.side-footer {
  border-top: 1px solid var(--adm-border);
  padding: 10px;
}
.account {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  border-radius: 9px;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: inherit;
}
.account:hover {
  background: #f7f7f8;
}
.avatar {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: #eef2f7;
  color: #475569;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.account-copy {
  min-width: 0;
  flex: 1;
}
.account-name {
  display: block;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.account-role {
  display: block;
  font-size: 10px;
  color: var(--adm-muted);
  margin-top: 2px;
}
.account-caret {
  color: var(--adm-muted-light);
  font-size: 11px;
}

/* ── Main / Topbar ───────────────────────── */
.main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.topbar {
  height: var(--adm-header-h);
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--adm-border);
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--adm-muted);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
}
.breadcrumb b {
  color: var(--adm-text-2);
  font-weight: 600;
}
.crumb-link:hover {
  color: var(--adm-text-2);
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.top-btn {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: 8px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}
.top-btn:hover {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}

/* 移动端菜单按钮:桌面隐藏 */
.menu-btn {
  display: none;
  width: 32px;
  height: 32px;
  padding: 0;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--adm-border);
  border-radius: 8px;
  background: var(--adm-surface);
  cursor: pointer;
}
.menu-btn i {
  width: 14px;
  height: 1.5px;
  background: var(--adm-muted);
  border-radius: 1px;
}
.mobile-backdrop {
  display: none;
}

/* 04 V2 §5:workspace padding 属于 Main,内容区在 Main 内限宽 */
.workspace {
  padding: var(--adm-workspace-pad);
  flex: 1;
  display: flex;
  flex-direction: column;
}
.content {
  width: min(var(--adm-content-max), 100%);
  margin: 0 auto;
  padding-bottom: 44px;
  flex: 1;
}

/* ── 响应式(04 §27)──────────────────────── */
@media (max-width: 1050px) {
  .app-shell {
    grid-template-columns: 204px minmax(0, 1fr);
  }
  .workspace {
    padding: 24px;
  }
}
@media (max-width: 719.98px) {
  .app-shell {
    grid-template-columns: 1fr;
  }
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 260;
    transform: translateX(-100%);
    transition: transform 0.18s ease;
    width: min(280px, 84vw);
  }
  .sidebar.open {
    transform: translateX(0);
  }
  .mobile-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 250;
    background: rgba(10, 10, 9, 0.32);
  }
  .menu-btn {
    display: inline-flex;
  }
  .topbar {
    padding: 0 18px;
  }
  .workspace {
    padding: 18px;
  }
}
</style>
