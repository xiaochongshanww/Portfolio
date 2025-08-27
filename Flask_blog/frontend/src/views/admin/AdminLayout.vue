<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="admin-sidebar">
      <div class="sidebar-header">
        <RouterLink to="/" class="logo-link">
          <div class="logo-container">
            <div class="logo-icon">
              <el-icon size="28"><EditPen /></el-icon>
            </div>
            <h2 class="logo">Blog CMS</h2>
          </div>
        </RouterLink>
        <div class="user-profile">
          <div class="user-avatar">
            <el-icon size="20"><User /></el-icon>
          </div>
          <div class="user-details">
            <p class="user-info">{{ userStore.user?.nickname || userStore.user?.email }}</p>
            <div class="role-badge" :class="`role-${userStore.user?.role}`">
              <span class="role-text">{{ getRoleText(userStore.user?.role) }}</span>
            </div>
          </div>
        </div>
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

          <!-- 日志管理 -->
          <el-menu-item 
            v-if="hasRole(['admin', 'editor'])" 
            index="/admin/logs" 
            route="/admin/logs"
          >
            <el-icon><Document /></el-icon>
            <span>日志管理</span>
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
            
            <el-menu-item index="/admin/backup" route="/admin/backup">
              <el-icon><FolderOpened /></el-icon>
              <span>备份管理</span>
            </el-menu-item>
            
            <el-menu-item index="/admin/restore" route="/admin/restore">
              <el-icon><RefreshLeft /></el-icon>
              <span>恢复任务</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </nav>

      <div class="sidebar-footer">
        <button @click="logout" class="logout-btn">
          <el-icon size="16"><SwitchButton /></el-icon>
          <span>退出登录</span>
        </button>
      </div>
    </aside>

    <!-- 主内容区域 -->
    <main class="admin-main">
      <!-- 顶部导航栏 -->
      <header class="admin-header">
        <div class="header-decoration"></div>
        <div class="header-content">
          <div class="header-left">
            <div class="breadcrumb-container">
              <el-icon class="breadcrumb-icon" size="18"><Location /></el-icon>
              <el-breadcrumb separator=">" class="modern-breadcrumb">
                <el-breadcrumb-item :to="{ path: '/admin' }">控制台</el-breadcrumb-item>
                <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.text" :to="item.to">
                  {{ item.text }}
                </el-breadcrumb-item>
              </el-breadcrumb>
            </div>
          </div>
          
          <div class="header-right">
            <div class="header-actions">
              <button @click="$router.push('/')" class="home-btn">
                <el-icon size="16"><HomeFilled /></el-icon>
                <span>返回网站</span>
              </button>
            </div>
          </div>
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
  HomeFilled, EditPen, Location, RefreshLeft 
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
  } else if (path.includes('/logs')) {
    crumbs.push({ text: '日志管理' });
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
/* ===== 现代化控制台样式 ===== */
.admin-layout {
  display: flex;
  height: 100vh;
  background: 
    radial-gradient(circle at 20% 80%, rgba(59, 130, 246, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 40% 40%, rgba(6, 182, 212, 0.03) 0%, transparent 50%),
    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  position: relative;
  overflow: hidden;
}

.admin-layout::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 2px 2px, rgba(59, 130, 246, 0.08) 1px, transparent 0);
  background-size: 40px 40px;
  opacity: 0.3;
  pointer-events: none;
  z-index: 1;
}

/* 侧边栏样式 */
.admin-sidebar {
  width: 280px;
  background: 
    linear-gradient(135deg, 
      rgba(255, 255, 255, 0.95) 0%, 
      rgba(248, 250, 252, 0.9) 100%
    );
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.3);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
  box-shadow: 
    0 0 0 1px rgba(255, 255, 255, 0.1),
    4px 0 20px -2px rgba(0, 0, 0, 0.05),
    8px 0 40px -4px rgba(0, 0, 0, 0.03);
}

.sidebar-header {
  padding: 2rem 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
}

.sidebar-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 1.5rem;
  right: 1.5rem;
  height: 1px;
  background: linear-gradient(
    90deg, 
    transparent 0%, 
    rgba(59, 130, 246, 0.3) 25%, 
    rgba(139, 92, 246, 0.3) 75%, 
    transparent 100%
  );
}

.logo-link {
  text-decoration: none;
  color: inherit;
  display: block;
  margin-bottom: 1.5rem;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.logo-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.25);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.logo-icon::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.2) 50%, transparent 60%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.logo-icon:hover {
  transform: scale(1.05) rotate(-2deg);
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.3);
}

.logo-icon:hover::before {
  transform: rotate(45deg) translateX(100%);
}

.logo {
  margin: 0;
  font-size: 1.375rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.025em;
}

/* 用户信息区域 */
.user-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.1);
  transition: all 0.3s ease;
}

.user-profile:hover {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.2);
  transform: scale(1.02);
}

.user-avatar {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #64748b, #475569);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.user-details {
  flex: 1;
  min-width: 0;
}

.user-info {
  margin: 0 0 0.375rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.role-admin {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.role-editor {
  background: rgba(245, 158, 11, 0.1);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.role-author {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.role-text {
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 导航菜单样式 */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 0;
}

.admin-menu {
  border-right: none;
  background: transparent !important;
}

.admin-menu :deep(.el-menu-item),
.admin-menu :deep(.el-sub-menu__title) {
  height: 48px;
  line-height: 48px;
  padding-left: 1.5rem !important;
  margin: 0.25rem 1rem;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  font-weight: 500;
}

.admin-menu :deep(.el-menu-item) {
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.admin-menu :deep(.el-menu-item::before) {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.05));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.admin-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.6);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateX(4px) scale(1.02);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15);
}

.admin-menu :deep(.el-menu-item:hover::before) {
  opacity: 1;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.1)) !important;
  color: #3b82f6 !important;
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 
    0 4px 20px rgba(59, 130, 246, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transform: translateX(8px) scale(1.05);
}

.admin-menu :deep(.el-menu-item.is-active::before) {
  opacity: 1;
}

.admin-menu :deep(.el-sub-menu__title) {
  background: rgba(255, 255, 255, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.15);
  font-weight: 600;
}

.admin-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.5);
  border-color: rgba(139, 92, 246, 0.3);
  transform: translateX(4px) scale(1.02);
  box-shadow: 0 4px 20px rgba(139, 92, 246, 0.15);
}

.admin-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(59, 130, 246, 0.1)) !important;
  color: #8b5cf6 !important;
  border-color: rgba(139, 92, 246, 0.3);
}

.admin-menu :deep(.el-menu-item .el-icon) {
  margin-right: 0.5rem;
  width: 18px;
  transition: all 0.3s ease;
}

.admin-menu :deep(.el-menu-item:hover .el-icon),
.admin-menu :deep(.el-menu-item.is-active .el-icon) {
  transform: scale(1.1);
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
}

.sidebar-footer::before {
  content: '';
  position: absolute;
  top: 0;
  left: 1.5rem;
  right: 1.5rem;
  height: 1px;
  background: linear-gradient(
    90deg, 
    transparent 0%, 
    rgba(139, 92, 246, 0.3) 25%, 
    rgba(59, 130, 246, 0.3) 75%, 
    transparent 100%
  );
}

.logout-btn {
  width: 100%;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(220, 38, 38, 0.05));
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 12px;
  color: #dc2626;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.logout-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(220, 38, 38, 0.05));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.logout-btn:hover {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1));
  border-color: rgba(239, 68, 68, 0.3);
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 8px 25px rgba(239, 68, 68, 0.2);
}

.logout-btn:hover::before {
  opacity: 1;
}

.logout-btn:active {
  transform: translateY(0) scale(0.98);
}

/* 主内容区域 */
.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  z-index: 2;
}

/* 顶部导航栏 */
.admin-header {
  height: 70px;
  background: 
    linear-gradient(135deg, 
      rgba(255, 255, 255, 0.95) 0%, 
      rgba(248, 250, 252, 0.9) 100%
    );
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  flex-shrink: 0;
  position: relative;
  box-shadow: 
    0 1px 3px rgba(0, 0, 0, 0.05),
    0 1px 2px rgba(0, 0, 0, 0.1);
}

.header-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    rgba(59, 130, 246, 0.02) 0%,
    rgba(139, 92, 246, 0.02) 50%,
    rgba(6, 182, 212, 0.02) 100%
  );
  pointer-events: none;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 2rem;
  position: relative;
  z-index: 2;
}

.header-left {
  flex: 1;
}

.breadcrumb-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.breadcrumb-icon {
  color: #64748b;
  opacity: 0.7;
}

.modern-breadcrumb :deep(.el-breadcrumb__item) {
  font-weight: 500;
}

.modern-breadcrumb :deep(.el-breadcrumb__inner) {
  color: #64748b;
  transition: color 0.3s ease;
}

.modern-breadcrumb :deep(.el-breadcrumb__inner:hover) {
  color: #3b82f6;
}

.modern-breadcrumb :deep(.el-breadcrumb__inner.is-link) {
  color: #3b82f6;
  font-weight: 600;
}

.header-right {
  flex-shrink: 0;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.home-btn {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.05));
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  color: #3b82f6;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.home-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.05));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.home-btn:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.1));
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.2);
}

.home-btn:hover::before {
  opacity: 1;
}

.home-btn:active {
  transform: translateY(0) scale(0.98);
}

/* 内容区域 */
.admin-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
  background: transparent;
  position: relative;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .admin-sidebar {
    width: 260px;
  }
  
  .sidebar-header {
    padding: 1.5rem 1rem;
  }
  
  .admin-menu :deep(.el-menu-item),
  .admin-menu :deep(.el-sub-menu__title) {
    margin: 0.25rem 0.75rem;
  }
}

@media (max-width: 768px) {
  .admin-layout {
    flex-direction: column;
  }
  
  .admin-sidebar {
    width: 100%;
    height: auto;
    max-height: 50vh;
  }
  
  .sidebar-header {
    padding: 1rem;
  }
  
  .logo-container {
    flex-direction: row;
    gap: 0.5rem;
  }
  
  .logo {
    font-size: 1.125rem;
  }
  
  .user-profile {
    padding: 0.75rem;
  }
  
  .sidebar-nav {
    max-height: 200px;
    padding: 0.5rem 0;
  }
  
  .admin-menu :deep(.el-menu-item),
  .admin-menu :deep(.el-sub-menu__title) {
    height: 44px;
    line-height: 44px;
    margin: 0.25rem 0.5rem;
    padding-left: 1rem !important;
  }
  
  .sidebar-footer {
    padding: 1rem;
  }
  
  .admin-header {
    height: 60px;
  }
  
  .header-content {
    padding: 0 1rem;
  }
  
  .admin-content {
    padding: 1rem;
  }
  
  .breadcrumb-container {
    gap: 0.5rem;
  }
  
  .modern-breadcrumb :deep(.el-breadcrumb__item) {
    font-size: 0.875rem;
  }
}

@media (max-width: 640px) {
  .header-content {
    flex-direction: column;
    gap: 0.75rem;
    align-items: flex-start;
  }
  
  .breadcrumb-container {
    width: 100%;
  }
  
  .header-actions {
    align-self: flex-end;
  }
  
  .home-btn {
    padding: 0.375rem 0.75rem;
    font-size: 0.875rem;
  }
}
</style>