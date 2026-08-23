<template>
  <div
    ref="headerRef" 
    class="rounded-lg shadow-sm transition-all duration-300"
    :class="{ 'shadow-md': isScrolled }"
  >
    <div class="px-6 py-4">
      <div class="flex justify-between items-center w-full">
        <!-- Logo + 品牌文字 -->
        <div class="flex-shrink-0">
          <a
            href="/"
            class="flex items-center text-blue-600 hover:text-blue-700 transition-colors logo-container"
            title="小重山的博客"
            @click="handleLogoClick"
          >
            <!-- Original SVG Logo -->
            <svg class="w-9 h-9 logo-icon" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
              <path d="M12 60 L32 44 L32 52 L18 60 L32 68 L32 76 Z" fill="#2563EB" opacity="0.32" />
              <path d="M108 60 L88 44 L88 52 L102 60 L88 68 L88 76 Z" fill="#2563EB" opacity="0.32" />
              <g stroke="#2563EB" stroke-width="3.25" fill="none" stroke-linecap="round">
                <path d="M20.5 92.5 L60.5 24.5 L100.5 92.5 Z" />
                <path d="M40.5 92.5 L60.5 24.5 L80.5 92.5 Z" />
                <path d="M20.5 92.5 L60.5 60.5 L100.5 92.5 Z" />
                <path d="M30.5 76.5 L60.5 60.5 L90.5 76.5" />
              </g>
              <g fill="#2563EB">
                <circle cx="60.5" cy="24.5" r="2.9" />
                <circle cx="20.5" cy="92.5" r="2.9" />
                <circle cx="100.5" cy="92.5" r="2.9" />
                <circle cx="40.5" cy="92.5" r="2.9" />
                <circle cx="80.5" cy="92.5" r="2.9" />
                <circle cx="60.5" cy="60.5" r="2.9" />
                <circle cx="30.5" cy="76.5" r="2.9" />
                <circle cx="90.5" cy="76.5" r="2.9" />
              </g>
            </svg>
            <span class="logo-text">小重山的博客</span>
          </a>
        </div>

        <!-- Desktop Navigation -->
        <nav class="desktop-nav items-center space-x-8 flex-1 justify-center">
          <a 
            href="/" 
            class="nav-link"
            :class="{ 'nav-link-active': $route.path === '/' }"
            @click="handleNavClick('/', $event)"
          >
            <el-icon class="mr-1"><HomeFilled /></el-icon>
            主页
          </a>
          <a 
            href="/archive" 
            class="nav-link"
            :class="{ 'nav-link-active': $route.path === '/archive' }"
            @click="handleNavClick('/archive', $event)"
          >
            <el-icon class="mr-1"><Calendar /></el-icon>
            归档
          </a>
          <a 
            href="/about" 
            class="nav-link"
            :class="{ 'nav-link-active': $route.path === '/about' }"
            @click="handleNavClick('/about', $event)"
          >
            <el-icon class="mr-1"><InfoFilled /></el-icon>
            关于
          </a>
        </nav>

        <!-- Desktop User Area -->
        <div class="desktop-user-area items-center flex-shrink-0">
          <!-- 未登录状态 -->
          <template v-if="!me">
            <router-link 
              to="/login" 
              style="margin-right: 16px; padding: 8px 16px; font-size: 1rem; font-weight: 500; color: rgb(55 65 81); background-color: rgb(249 250 251); border: 1px solid rgb(229 231 235); border-radius: 8px; transition: all 0.2s ease; text-decoration: none;"
            >
              登录
            </router-link>
            <router-link 
              to="/register"
              style="display: inline-flex; align-items: center; padding: 8px 16px; border: 1px solid transparent; font-size: 1rem; font-weight: 500; border-radius: 8px; color: white; background-color: rgb(37 99 235); transition: all 0.2s ease; text-decoration: none;"
            >
              注册
            </router-link>
          </template>

          <!-- 已登录状态 -->
          <template v-else>
            <!-- 写文章按钮 - 主要CTA -->
            <router-link 
              to="/articles/new"
              class="write-article-btn"
            >
              <el-icon class="text-base"><EditPen /></el-icon>
              <span class="write-article-text">写文章</span>
            </router-link>

            <!-- 用户头像下拉菜单 -->
            <el-dropdown trigger="click" @command="handleCommand">
              <div class="user-dropdown-trigger">
                <div class="user-avatar-container">
                  <img 
                    v-if="me.avatar" 
                    :src="me.avatar" 
                    :alt="me.nickname || me.email"
                    class="user-avatar-img"
                    @error="handleAvatarError"
                  >
                  <el-icon v-else class="user-avatar-icon"><User /></el-icon>
                </div>
                <div class="user-info">
                  <div class="user-name" :title="getUserDisplayHint(me)">{{ userDisplayName }}</div>
                  <div v-if="shouldShowNicknamePrompt" class="nickname-prompt">
                    <span class="prompt-text">未设置昵称</span>
                  </div>
                </div>
                <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="me.id" :command="`/author/${me.id}`">
                    <el-icon><User /></el-icon>
                    个人主页
                  </el-dropdown-item>
                  <el-dropdown-item command="/me/profile">
                    <el-icon><Setting /></el-icon>
                    个人设置
                    <span v-if="shouldShowNicknamePrompt" class="ml-2 text-xs text-blue-600">
                      (设置昵称)
                    </span>
                  </el-dropdown-item>
                  <el-dropdown-item command="/media">
                    <el-icon><Picture /></el-icon>
                    我的媒体库
                  </el-dropdown-item>
                  <el-dropdown-item v-if="userStore.canAccessAdmin" divided>
                    管理功能
                  </el-dropdown-item>
                  <el-dropdown-item v-if="userStore.canAccessAdmin" :command="'/admin'">
                    <el-icon><DataBoard /></el-icon>
                    管理控制台
                  </el-dropdown-item>
                  <el-dropdown-item v-if="me.role === 'admin'" :command="'/admin/users'">
                    <el-icon><UserFilled /></el-icon>
                    用户管理
                  </el-dropdown-item>
                  <el-dropdown-item v-if="me.role === 'editor' || me.role === 'admin'" :command="'/admin/metrics'">
                    <el-icon><DataAnalysis /></el-icon>
                    统计分析
                  </el-dropdown-item>
                  <el-dropdown-item command="logout" divided>
                    <el-icon><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </div>

        <!-- Mobile Menu Button -->
        <div class="mobile-menu-btn items-center">
          <button
            class="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 transition-colors"
            type="button"
            aria-label="打开菜单"
            @click="drawer = true"
          >
            <el-icon size="20"><Menu /></el-icon>
          </button>
        </div>
      </div>
    </div>

    <!-- Mobile Drawer -->
    <el-drawer 
      v-model="drawer" 
      title="菜单" 
      direction="rtl" 
      size="80%"
      class="mobile-drawer"
      :z-index="4000"
      append-to-body
    >
      <div class="flex flex-col h-full">
        <!-- 移动端用户信息 -->
        <div v-if="me" class="p-4 bg-gray-50 border-b">
          <div class="flex items-center">
            <div class="w-12 h-12 rounded-full overflow-hidden bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center">
              <img 
                v-if="me.avatar" 
                :src="me.avatar" 
                :alt="me.nickname || me.email"
                class="w-full h-full object-cover"
              >
              <el-icon v-else class="text-white"><User /></el-icon>
            </div>
            <div class="ml-3">
              <div class="font-medium text-gray-900">{{ userDisplayName }}</div>
              <div class="text-sm text-gray-500">{{ me.email }}</div>
              <div v-if="shouldShowNicknamePrompt" class="text-xs text-blue-600 mt-1">
                点击设置昵称
              </div>
            </div>
          </div>
        </div>

        <!-- 移动端导航 -->
        <div class="flex-1 py-4">
          <nav class="space-y-1">
            <a 
              href="/" 
              class="mobile-nav-link"
              :class="{ 'mobile-nav-link-active': $route.path === '/' }"
              @click="handleMobileHomeClick"
            >
              <el-icon class="mr-3"><HomeFilled /></el-icon>
              主页
            </a>
            
            <router-link 
              to="/archive" 
              class="mobile-nav-link" 
              :class="{ 'mobile-nav-link-active': $route.path === '/archive' }"
              @click="drawer = false"
            >
              <el-icon class="mr-3"><Calendar /></el-icon>
              归档
            </router-link>
            
            <router-link 
              to="/about" 
              class="mobile-nav-link" 
              @click="drawer = false"
            >
              <el-icon class="mr-3"><InfoFilled /></el-icon>
              关于
            </router-link>

            <!-- 移动端侧边栏组件 -->
            <MobileSidebar 
              :categories="sidebarCategories"
              :tags="sidebarTags"
              :hot-articles="hotArticles"
              :latest-articles="[]"
              @category-click="handleCategoryClick"
              @tag-click="handleTagClick"
              @article-click="handleArticleClick"
              @close="drawer = false"
            />

            <div v-if="me" class="pt-4 border-t border-gray-200">
              <router-link 
                to="/articles/new" 
                class="mobile-nav-link" 
                @click="drawer = false"
              >
                <el-icon class="mr-3"><EditPen /></el-icon>
                写文章
              </router-link>
              
              <router-link 
                v-if="me.id" 
                :to="`/author/${me.id}`" 
                class="mobile-nav-link"
                @click="drawer = false"
              >
                <el-icon class="mr-3"><User /></el-icon>
                我的主页
              </router-link>
              
              <router-link 
                to="/me/profile" 
                class="mobile-nav-link" 
                @click="drawer = false"
              >
                <el-icon class="mr-3"><Setting /></el-icon>
                设置
              </router-link>
              
              <router-link 
                to="/media" 
                class="mobile-nav-link" 
                @click="drawer = false"
              >
                <el-icon class="mr-3"><Picture /></el-icon>
                我的媒体库
              </router-link>
            </div>

            <!-- 管理功能 -->
            <div v-if="me && (me.role === 'editor' || me.role === 'admin')" class="pt-4 border-t border-gray-200">
              <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">管理功能</div>
              
              
              <router-link 
                v-if="me.role === 'admin'" 
                to="/admin/users" 
                class="mobile-nav-link"
                @click="drawer = false"
              >
                <el-icon class="mr-3"><UserFilled /></el-icon>
                用户管理
              </router-link>
              
              <router-link 
                to="/admin/metrics" 
                class="mobile-nav-link" 
                @click="drawer = false"
              >
                <el-icon class="mr-3"><DataAnalysis /></el-icon>
                统计分析
              </router-link>
            </div>
          </nav>
        </div>

        <!-- 移动端底部操作 -->
        <div class="border-t border-gray-200 p-4">
          <div v-if="!me" class="space-y-3">
            <router-link 
              to="/login" 
              class="block w-full text-center py-2 px-4 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              @click="drawer = false"
            >
              登录
            </router-link>
            <router-link 
              to="/register" 
              class="block w-full text-center py-2 px-4 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              @click="drawer = false"
            >
              注册
            </router-link>
          </div>
          
          <button 
            v-else
            class="w-full flex items-center justify-center py-2 px-4 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            @click="handleLogout"
          >
            <el-icon class="mr-2"><SwitchButton /></el-icon>
            退出登录
          </button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useUserStore } from '../../stores/user';
import { ElMessage } from 'element-plus';
import { getUserDisplayName, getUserShortName, shouldPromptNickname, getNicknameSuggestion, getUserDisplayHint } from '../../utils/userDisplay';
import {
  User, EditPen, ArrowDown, Setting, UserFilled, DataAnalysis,
  SwitchButton, Menu, HomeFilled, TrendCharts, InfoFilled, DataBoard, Calendar
} from '@element-plus/icons-vue';
import MobileSidebar from '../sidebar/MobileSidebar.vue';

// 接收滚动状态作为prop
const props = defineProps({
  isScrolled: {
    type: Boolean,
    default: false
  },
  sidebarData: {
    type: Object,
    default: () => ({
      categories: [],
      tags: [],
      hotArticles: []
    })
  }
});

const router = useRouter();
const drawer = ref(false);
const userStore = useUserStore();
const { user: me } = storeToRefs(userStore);
const headerRef = ref(null);

// 从props获取侧边栏数据
const sidebarCategories = computed(() => props.sidebarData?.categories?.slice(0, 6) || []);
const sidebarTags = computed(() => props.sidebarData?.tags?.slice(0, 8) || []);
const hotArticles = computed(() => props.sidebarData?.hotArticles?.slice(0, 3) || []);

// 用户显示名称计算属性
const userDisplayName = computed(() => {
  if (!me.value) return ''
  return getUserDisplayName(me.value, { maxLength: 12 })
})

const userShortName = computed(() => {
  if (!me.value) return ''
  return getUserShortName(me.value, 8)
})

const shouldShowNicknamePrompt = computed(() => {
  return me.value && shouldPromptNickname(me.value)
})

const nicknameSuggestion = computed(() => {
  return me.value ? getNicknameSuggestion(me.value) : null
})

// 处理下拉菜单命令
/** @param {string} command */
function handleCommand(command) {
  if (command === 'logout') {
    handleLogout();
  } else {
    router.push(command);
  }
}

// 处理退出登录
async function handleLogout() {
  try {
    await userStore.logout();
    drawer.value = false;
    
    // 创建一个标记来控制MessageBox的关闭
    let shouldAllowClose = false;
    
    // 使用 MessageBox 显示退出成功确认
    const messageBoxPromise = ElMessageBox({
      title: '👋 退出成功',
      message: `
        <div style="text-align: center; padding: 20px 0;">
          <div style="font-size: 48px; margin-bottom: 16px;">🌙</div>
          <div style="font-size: 18px; font-weight: 600; color: #6366f1; margin-bottom: 8px;">
            再见！
          </div>
          <div style="font-size: 14px; color: #6b7280; margin-bottom: 16px;">
            您已安全退出，正在返回主页...
          </div>
          <div style="width: 200px; height: 4px; background: #f3f4f6; border-radius: 2px; margin: 0 auto; overflow: hidden;">
            <div style="width: 100%; height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); border-radius: 2px; animation: progressBar 2s ease-in-out;"></div>
          </div>
        </div>
      `,
      dangerouslyUseHTMLString: true,
      showCancelButton: false,
      showConfirmButton: false,
      showClose: false,
      center: true,
      customClass: 'logout-success-dialog',
      beforeClose: (action, instance, done) => {
        if (shouldAllowClose) {
          done();
        } else {
          return false;
        }
      }
    }).catch(() => {
      console.log('退出确认对话框已关闭');
    });
    
    // 2秒后自动关闭对话框并跳转
    setTimeout(() => {
      console.log('🚪 用户退出登录，强制刷新主页数据');
      
      shouldAllowClose = true;
      ElMessageBox.close();
      
      // 退出登录后强制刷新主页数据
      router.push({ path: '/', query: { _refresh: Date.now() } });
    }, 2000);
    
  } catch (error) {
    ElMessage.error('退出登录失败');
  }
}

// 处理头像加载错误
/** @param {Event} e */
function handleAvatarError(e) {
  const img = /** @type {HTMLElement} */ (e.target);
  img.style.display = 'none';
}

// 移动端汉堡菜单中的处理函数
/** @param {number | string} categoryId */
function handleCategoryClick(categoryId) {
  router.push({ path: '/', query: { category_id: categoryId } });
  drawer.value = false;
}

/** @param {string} tagSlug */
function handleTagClick(tagSlug) {
  router.push({ path: '/', query: { tag: tagSlug } });
  drawer.value = false;
}

/** @param {string} articleSlug */
function handleArticleClick(articleSlug) {
  router.push(`/article/${articleSlug}`);
  drawer.value = false;
}

// 处理Logo点击 - 使用原生导航避免组件状态冲突
/** @param {MouseEvent} e */
function handleLogoClick(e) {
  console.log('🏠 AppHeader: Logo点击，检查是否需要原生导航');
  
  // 检查当前路由是否为文章编辑页面
  const currentPath = router.currentRoute.value.path;
  const isOnNewArticlePage = currentPath === '/articles/new';
  
  if (isOnNewArticlePage) {
    console.log('🏠 AppHeader: 当前在文章编辑页面，使用原生导航避免VNode冲突');
    e.preventDefault();
    
    // 使用原生导航，但手动添加刷新参数
    console.log('🏠 从编辑页通过Logo原生导航到主页，添加刷新标记');
    window.location.href = `/?_refresh=${Date.now()}`;
    return;
  }
  
  // 其他页面使用正常的Vue Router导航
  e.preventDefault();
  console.log('🏠 AppHeader: 从其他页面导航到主页，添加刷新标记');
  
  // 添加一个特殊的查询参数来触发数据刷新
  const shouldRefresh = currentPath !== '/' && currentPath !== '/home';
  console.log('🔍 导航判断:', { currentPath, shouldRefresh });
  
  if (shouldRefresh) {
    console.log('🏷️ 添加刷新标记进行导航');
    router.push({ path: '/', query: { _refresh: Date.now() } });
  } else {
    console.log('📍 直接导航到主页');
    router.push('/');
  }
}

// 处理导航链接点击 - 智能选择导航方式
/** @param {string} path @param {MouseEvent} e */
function handleNavClick(path, e) {
  console.log(`🧭 AppHeader: 导航到 ${path}，检查是否需要原生导航`);
  
  // 检查当前路由是否为文章编辑页面
  const currentPath = router.currentRoute.value.path;
  const isOnNewArticlePage = currentPath === '/articles/new';
  
  if (isOnNewArticlePage) {
    console.log('🧭 AppHeader: 当前在文章编辑页面，使用原生导航避免VNode冲突');
    e.preventDefault();
    
    // 虽然我们修复了一些VNode问题，但组件卸载时仍有冲突
    // 使用原生导航，但手动添加刷新参数
    if (path === '/' || path === '/home') {
      console.log('🏠 从编辑页原生导航到主页，添加刷新标记');
      window.location.href = `/?_refresh=${Date.now()}`;
    } else {
      console.log('🔗 从编辑页原生导航到其他页面');
      window.location.href = path;
    }
    return;
  }
  
  // 其他页面使用正常的Vue Router导航
  e.preventDefault();
  
  // 如果是导航到主页，应用与Logo点击相同的刷新逻辑
  if (path === '/' || path === '/home') {
    console.log('🏠 AppHeader: 主页导航，检查是否需要刷新标记');
    
    const shouldRefresh = currentPath !== '/' && currentPath !== '/home';
    console.log('🔍 导航判断:', { currentPath, shouldRefresh, targetPath: path });
    
    if (shouldRefresh) {
      console.log('🏷️ 添加刷新标记进行主页导航');
      router.push({ path: '/', query: { _refresh: Date.now() } });
    } else {
      console.log('📍 直接导航到主页');
      router.push(path);
    }
  } else {
    // 其他路径的正常导航
    router.push(path);
  }
}

// 处理移动端主页点击
/** @param {MouseEvent} e */
function handleMobileHomeClick(e) {
  console.log('📱 AppHeader: 移动端主页点击');
  
  // 关闭移动端抽屉
  drawer.value = false;
  
  // 使用与Logo点击相同的逻辑
  handleLogoClick(e);
}
</script>

<style scoped>
/* 内容区域样式 - 渐变效果由外层header容器处理 */

/* 导航链接样式 */
.nav-link {
  display: flex;
  align-items: center;
  color: rgb(75 85 99);
  font-weight: 500;
  font-size: 1rem;
  transition: color 0.2s ease;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  text-decoration: none;
}

.nav-link:hover {
  color: rgb(37 99 235);
  background-color: rgb(239 246 255);
}

.nav-link-active {
  color: rgb(37 99 235);
  background-color: rgb(239 246 255);
}

/* 移动端导航链接样式 */
.mobile-nav-link {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  font-weight: 500;
  color: rgb(75 85 99);
  transition: color 0.2s ease;
  border-radius: 0.5rem;
  margin: 0 0.5rem;
}

.mobile-nav-link:hover {
  color: rgb(37 99 235);
  background-color: rgb(239 246 255);
}

.mobile-nav-link-active {
  color: rgb(37 99 235);
  background-color: rgb(239 246 255);
}

/* 滚动时增强阴影效果 */
.header-scrolled {
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}

/* 下拉菜单样式增强 */
:deep(.el-dropdown-menu) {
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
  border-color: rgb(243 244 246);
}

:deep(.el-dropdown-menu__item) {
  font-size: 0.875rem;
}

:deep(.el-dropdown-menu__item:hover) {
  background-color: rgb(239 246 255);
  color: rgb(37 99 235);
}

/* 移动端抽屉样式和z-index层级管理 */
:deep(.mobile-drawer) {
  z-index: 4000 !important;
}

:deep(.mobile-drawer .el-drawer__wrapper) {
  z-index: 4000 !important;
}

:deep(.mobile-drawer .el-overlay) {
  z-index: 4000 !important;
}

:deep(.mobile-drawer .el-drawer) {
  z-index: 4001 !important;
}

:deep(.mobile-drawer .el-drawer__header) {
  border-bottom: 1px solid rgb(229 231 235);
  padding-bottom: 1rem;
}

:deep(.mobile-drawer .el-drawer__title) {
  font-weight: 600;
  color: rgb(17 24 39);
}

/* Logo容器和图标样式 - 确保显示 */
.logo-container {
  padding: 8px;
  border-radius: 12px;
  transition: all 0.2s ease-in-out;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-container:hover {
  background-color: rgba(59, 130, 246, 0.05);
}

.logo-container:hover .logo-icon {
  transform: scale(1.05);
  transition: transform 0.2s ease-in-out;
}

.logo-icon {
  transition: transform 0.2s ease-in-out;
  display: block;
  width: 2.25rem; /* 缩小图标,为品牌文字留空间 */
  height: 2.25rem;
  flex-shrink: 0;
}

/* 品牌文字 */
.logo-text {
  margin-left: 0.5rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: rgb(17 24 39);
  white-space: nowrap;
  letter-spacing: 0.01em;
  transition: color 0.2s ease;
}

.logo-container:hover .logo-text {
  color: rgb(37 99 235);
}

/* 确保SVG内容可见 */
.logo-icon path,
.logo-icon circle,
.logo-icon g {
  display: block;
  visibility: visible;
}

/* 调试边框已移除 */

/* 用户下拉菜单 hover 效果 */
.user-dropdown:hover {
  background-color: rgb(249 250 251);
}

/* 确保响应式断点正确工作 - 使用更强的优先级 */
@media (max-width: 767.98px) {
  /* 移动端：强制隐藏桌面元素 */
  nav.desktop-nav {
    display: none !important;
  }
  div.desktop-user-area {
    display: none !important;
  }
  div.mobile-menu-btn {
    display: flex !important;
  }
}

@media (min-width: 768px) {
  /* 桌面端：强制显示桌面元素，隐藏移动端元素 */
  nav.desktop-nav {
    display: flex !important;
  }
  div.desktop-user-area {
    display: flex !important;
  }
  div.mobile-menu-btn {
    display: none !important;
  }
}

/* 登录按钮悬停效果 */
a[href="/login"]:hover {
  background-color: rgb(243 244 246) !important;
  border-color: rgb(209 213 219) !important;
  color: rgb(37 99 235) !important;
}

/* 注册按钮悬停效果 */
a[href="/register"]:hover {
  background-color: rgb(29 78 216) !important;
}

/* ===== 登录后用户区域样式优化 ===== */

/* 写文章按钮 - 主要CTA样式 */
.write-article-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  margin-right: 16px;
  background: linear-gradient(135deg, rgb(59 130 246), rgb(37 99 235));
  color: white;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgb(59 130 246 / 0.2);
}

.write-article-btn:hover {
  background: linear-gradient(135deg, rgb(37 99 235), rgb(29 78 216));
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgb(59 130 246 / 0.3);
  color: white;
}

.write-article-btn:active {
  transform: translateY(0);
}

/* 写文章按钮文字在小屏幕隐藏 */
@media (max-width: 640px) {
  .write-article-text {
    display: none;
  }
  .write-article-btn {
    padding: 10px 12px;
    margin-right: 12px;
  }
}

/* 用户下拉菜单触发器 */
.user-dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  background: rgb(248 250 252);
}

.user-dropdown-trigger:hover {
  background: rgb(241 245 249);
  border-color: rgb(226 232 240);
  box-shadow: 0 2px 4px rgb(0 0 0 / 0.05);
}

/* 用户头像容器 */
.user-avatar-container {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, rgb(59 130 246), rgb(139 92 246));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgb(59 130 246 / 0.2);
}

.user-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-avatar-icon {
  color: white;
  font-size: 18px;
}

/* 用户信息 */
.user-info {
  flex: 1;
  min-width: 0; /* 允许文本截断 */
}

.user-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: rgb(17 24 39);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

/* 下拉箭头 */
.dropdown-arrow {
  color: rgb(107 114 128);
  font-size: 14px;
  transition: transform 0.2s ease;
}

.user-dropdown-trigger:hover .dropdown-arrow {
  color: rgb(59 130 246);
}

/* 昵称提示样式 */
.nickname-prompt {
  margin-top: 2px;
}

.prompt-text {
  font-size: 0.75rem;
  color: rgb(59 130 246);
  font-weight: 500;
}

/* 移动端用户区域优化 */
@media (max-width: 640px) {
  .user-info {
    display: none;
  }
  .user-dropdown-trigger {
    padding: 8px;
    gap: 0;
  }
  .dropdown-arrow {
    display: none;
  }
}

/* line-clamp utilities */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
}
</style>
