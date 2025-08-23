<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="admin-sidebar">
      <div class="sidebar-header">
        <RouterLink to="/" class="logo-link">
          <h2 class="logo">📝 Blog CMS</h2>
        </RouterLink>
        <p class="user-info">{{ userStore.user?.nickname || userStore.user?.email }}</p>
        <el-tag :type="getRoleType(userStore.user?.role)" size="small">
          {{ getRoleText(userStore.user?.role) }}
        </el-tag>
      </div>

      <nav class="sidebar-nav">
        <el-menu 
          :default-active="activeMenuKey" 
          class="admin-menu"
          router
          background-color="#f8f9fa"
          text-color="#495057"
          active-text-color="#007bff"
        >
          <!-- 仪表盘 -->
          <el-menu-item index="/admin" route="/admin">
            <el-icon><DataBoard /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>

          <!-- 内容管理 -->
          <el-sub-menu index="content">
            <template #title>
              <el-icon><Document /></el-icon>
              <span>内容管理</span>
            </template>
            
            <el-menu-item index="/admin/articles" route="/admin/articles">
              <el-icon><Edit /></el-icon>
              <span>文章管理</span>
            </el-menu-item>
            
            <el-menu-item 
              v-if="hasRole(['editor', 'admin'])" 
              index="/admin/articles/review" 
              route="/admin/articles/review"
            >
              <el-icon><View /></el-icon>
              <span>文章审核</span>
            </el-menu-item>
            
            <el-menu-item 
              v-if="hasRole(['editor', 'admin'])" 
              index="/admin/comments" 
              route="/admin/comments"
            >
              <el-icon><ChatLineRound /></el-icon>
              <span>评论管理</span>
            </el-menu-item>
          </el-sub-menu>

          <!-- 分类标签 -->
          <el-sub-menu v-if="hasRole(['editor', 'admin'])" index="taxonomy">
            <template #title>
              <el-icon><Collection /></el-icon>
              <span>分类标签</span>
            </template>
            
            <el-menu-item index="/admin/categories" route="/admin/categories">
              <el-icon><FolderOpened /></el-icon>
              <span>分类管理</span>
            </el-menu-item>
            
            <el-menu-item index="/admin/tags" route="/admin/tags">
              <el-icon><PriceTag /></el-icon>
              <span>标签管理</span>
            </el-menu-item>
          </el-sub-menu>

          <!-- 用户管理 -->
          <el-menu-item 
            v-if="hasRole(['admin'])" 
            index="/admin/users" 
            route="/admin/users"
          >
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>

          <!-- 安全监控 -->
          <el-menu-item 
            v-if="hasRole(['admin', 'editor'])" 
            index="/admin/security" 
            route="/admin/security"
          >
            <el-icon><Lock /></el-icon>
            <span>安全监控</span>
          </el-menu-item>

          <!-- 系统设置 -->
          <el-sub-menu v-if="hasRole(['admin'])" index="settings">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </template>
            
            <el-menu-item index="/admin/settings/general" route="/admin/settings/general">
              <el-icon><Tools /></el-icon>
              <span>基本设置</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </nav>

      <div class="sidebar-footer">
        <el-button @click="logout" type="danger" size="small" plain>
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </aside>

    <!-- 主内容区域 -->
    <main class="admin-main">
      <!-- 顶部导航栏 -->
      <header class="admin-header">
        <div class="header-left">
          <el-breadcrumb separator=">">
            <el-breadcrumb-item :to="{ path: '/admin' }">控制台</el-breadcrumb-item>
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.text" :to="item.to">
              {{ item.text }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-button @click="$router.push('/')" type="primary" size="small" plain>
            <el-icon><HomeFilled /></el-icon>
            返回网站
          </el-button>
        </div>
      </header>

      <!-- 页面内容 -->
      <div class="admin-content">
        <RouterView />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { 
  DataBoard, Document, Edit, View, ChatLineRound, Collection, 
  FolderOpened, PriceTag, User, Lock, Setting, Tools, SwitchButton, 
  HomeFilled 
} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '../../stores/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

// 当前激活的菜单项
const activeMenuKey = computed(() => route.path);

// 面包屑导航
const breadcrumbs = computed(() => {
  const path = route.path;
  const crumbs: Array<{text: string, to?: string}> = [];
  
  if (path.includes('/articles/review')) {
    crumbs.push({ text: '内容管理' });
    crumbs.push({ text: '文章审核' });
  } else if (path.includes('/articles')) {
    crumbs.push({ text: '内容管理' });
    crumbs.push({ text: '文章管理' });
  } else if (path.includes('/comments')) {
    crumbs.push({ text: '内容管理' });
    crumbs.push({ text: '评论管理' });
  } else if (path.includes('/categories')) {
    crumbs.push({ text: '分类标签' });
    crumbs.push({ text: '分类管理' });
  } else if (path.includes('/tags')) {
    crumbs.push({ text: '分类标签' });
    crumbs.push({ text: '标签管理' });
  } else if (path.includes('/users')) {
    crumbs.push({ text: '用户管理' });
  } else if (path.includes('/security')) {
    crumbs.push({ text: '安全监控' });
  } else if (path.includes('/settings')) {
    crumbs.push({ text: '系统设置' });
    if (path.includes('/general')) {
      crumbs.push({ text: '基本设置' });
    }
  }
  
  return crumbs;
});

// 权限检查
function hasRole(roles: string[]): boolean {
  return roles.includes(userStore.user?.role || '');
}

function getRoleType(role?: string): string {
  switch (role) {
    case 'admin': return 'danger';
    case 'editor': return 'warning';  
    case 'author': return 'info';
    default: return '';
  }
}

function getRoleText(role?: string): string {
  switch (role) {
    case 'admin': return '管理员';
    case 'editor': return '编辑';
    case 'author': return '作者';
    default: return '用户';
  }
}

// 退出登录
async function logout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    await userStore.logout();
    ElMessage.success('已退出登录');
    router.push('/login');
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  height: 100vh;
  background-color: #f5f5f5;
}

.admin-sidebar {
  width: 250px;
  background-color: #f8f9fa;
  border-right: 1px solid #dee2e6;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #dee2e6;
  text-align: center;
}

.logo-link {
  text-decoration: none;
  color: inherit;
}

.logo {
  margin: 0 0 8px 0;
  color: #495057;
  font-size: 18px;
}

.user-info {
  margin: 8px 0 4px 0;
  font-size: 14px;
  color: #6c757d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
}

.admin-menu {
  border-right: none;
}

.admin-menu :deep(.el-menu-item),
.admin-menu :deep(.el-sub-menu__title) {
  height: 48px;
  line-height: 48px;
  padding-left: 20px !important;
}

.admin-menu :deep(.el-menu-item) {
  margin: 2px 0;
  border-radius: 8px;
  margin-left: 8px;
  margin-right: 8px;
  width: calc(100% - 16px);
}

.admin-menu :deep(.el-menu-item.is-active) {
  background-color: #e3f2fd !important;
  color: #1976d2 !important;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid #dee2e6;
}

.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.admin-header {
  height: 60px;
  background-color: white;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.header-left {
  flex: 1;
}

.header-right {
  flex-shrink: 0;
}

.admin-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background-color: #f5f5f5;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .admin-layout {
    flex-direction: column;
  }
  
  .admin-sidebar {
    width: 100%;
    height: auto;
  }
  
  .sidebar-nav {
    max-height: 200px;
  }
  
  .admin-content {
    padding: 16px;
  }
}
</style>