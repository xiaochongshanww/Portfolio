<template>
  <div class="rounded-lg shadow-sm transition-all duration-300" 
    :class="{ 'shadow-md': isScrolled }"
    ref="headerRef"
  >
    <div class="px-6 py-4">
      <div class="flex justify-between items-center w-full">
        <!-- Logo -->
        <div class="flex-shrink-0">
          <a 
            href="/" 
            @click="handleLogoClick"
            class="flex items-center text-xl font-bold text-blue-600 hover:text-blue-700 transition-colors logo-container"
          >
            <!-- Simple SVG Logo -->
            <svg class="w-10 h-10 mr-3 logo-icon" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="40" height="40" rx="8" fill="url(#paint0_linear)"/>
              <path d="M12 28V12h6c2.2 0 4 1.8 4 4 0 1.2-.6 2.2-1.4 2.8.8.6 1.4 1.6 1.4 2.8 0 2.2-1.8 4-4 4h-6z" fill="white"/>
              <path d="M16 16h2c.6 0 1 .4 1 1s-.4 1-1 1h-2v-2z" fill="url(#paint0_linear)"/>
              <path d="M16 22h2.5c.8 0 1.5.7 1.5 1.5s-.7 1.5-1.5 1.5H16v-3z" fill="url(#paint0_linear)"/>
              <defs>
                <linearGradient id="paint0_linear" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#3B82F6"/>
                  <stop offset="1" stop-color="#8B5CF6"/>
                </linearGradient>
              </defs>
            </svg>
            小重山的博客
          </a>
        </div>

        <!-- Desktop Navigation -->
        <nav class="desktop-nav items-center space-x-8 flex-1 justify-center">
          <a 
            href="/" 
            @click="handleNavClick('/', $event)"
            class="nav-link"
            :class="{ 'nav-link-active': $route.path === '/' }"
          >
            <el-icon class="mr-1"><HomeFilled /></el-icon>
            主页
          </a>
          <a 
            href="/categories" 
            @click="handleNavClick('/categories', $event)"
            class="nav-link"
            :class="{ 'nav-link-active': $route.path.startsWith('/category') }"
          >
            <el-icon class="mr-1"><Collection /></el-icon>
            分类浏览
          </a>
          <a 
            href="/about" 
            @click="handleNavClick('/about', $event)"
            class="nav-link"
            :class="{ 'nav-link-active': $route.path === '/about' }"
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
            <el-dropdown @command="handleCommand" trigger="click">
              <div class="user-dropdown-trigger">
                <div class="user-avatar-container">
                  <img 
                    v-if="me.avatar" 
                    :src="me.avatar" 
                    :alt="me.nickname || me.email"
                    class="user-avatar-img"
                    @error="handleAvatarError"
                  />
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
                  <el-dropdown-item :command="`/author/${me.id}`" v-if="me.id">
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
                  <el-dropdown-item divided v-if="userStore.canAccessAdmin">
                    管理功能
                  </el-dropdown-item>
                  <el-dropdown-item :command="'/admin'" v-if="userStore.canAccessAdmin">
                    <el-icon><DataBoard /></el-icon>
                    管理控制台
                  </el-dropdown-item>
                  <el-dropdown-item :command="'/admin/taxonomy'" v-if="me.role === 'editor' || me.role === 'admin'">
                    <el-icon><Collection /></el-icon>
                    分类标签
                  </el-dropdown-item>
                  <el-dropdown-item :command="'/admin/users'" v-if="me.role === 'admin'">
                    <el-icon><UserFilled /></el-icon>
                    用户管理
                  </el-dropdown-item>
                  <el-dropdown-item :command="'/admin/metrics'" v-if="me.role === 'editor' || me.role === 'admin'">
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
            @click="drawer = true"
            class="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 transition-colors"
            type="button"
            aria-label="打开菜单"
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
              />
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
              @click="handleMobileHomeClick"
              class="mobile-nav-link"
              :class="{ 'mobile-nav-link-active': $route.path === '/' }"
            >
              <el-icon class="mr-3"><HomeFilled /></el-icon>
              主页
            </a>
            
            <router-link 
              to="/categories" 
              @click="drawer = false" 
              class="mobile-nav-link"
            >
              <el-icon class="mr-3"><Collection /></el-icon>
              分类浏览
            </router-link>
            
            
            <router-link 
              to="/about" 
              @click="drawer = false" 
              class="mobile-nav-link"
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
                @click="drawer = false" 
                class="mobile-nav-link"
              >
                <el-icon class="mr-3"><EditPen /></el-icon>
                写文章
              </router-link>
              
              <router-link 
                :to="`/author/${me.id}`" 
                @click="drawer = false" 
                class="mobile-nav-link"
                v-if="me.id"
              >
                <el-icon class="mr-3"><User /></el-icon>
                我的主页
              </router-link>
              
              <router-link 
                to="/me/profile" 
                @click="drawer = false" 
                class="mobile-nav-link"
              >
                <el-icon class="mr-3"><Setting /></el-icon>
                设置
              </router-link>
            </div>

            <!-- 管理功能 -->
            <div v-if="me && (me.role === 'editor' || me.role === 'admin')" class="pt-4 border-t border-gray-200">
              <div class="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">管理功能</div>
              
              <router-link 
                to="/admin/taxonomy" 
                @click="drawer = false" 
                class="mobile-nav-link"
              >
                <el-icon class="mr-3"><Collection /></el-icon>
                分类标签
              </router-link>
              
              <router-link 
                to="/admin/users" 
                @click="drawer = false" 
                class="mobile-nav-link"
                v-if="me.role === 'admin'"
              >
                <el-icon class="mr-3"><UserFilled /></el-icon>
                用户管理
              </router-link>
              
              <router-link 
                to="/admin/metrics" 
                @click="drawer = false" 
                class="mobile-nav-link"
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
              @click="drawer = false"
              class="block w-full text-center py-2 px-4 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              登录
            </router-link>
            <router-link 
              to="/register" 
              @click="drawer = false"
              class="block w-full text-center py-2 px-4 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              注册
            </router-link>
          </div>
          
          <button 
            v-else
            @click="handleLogout"
            class="w-full flex items-center justify-center py-2 px-4 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
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
  User, EditPen, ArrowDown, Setting, Collection, UserFilled, DataAnalysis,
  SwitchButton, Menu, HomeFilled, TrendCharts, InfoFilled, DataBoard
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
    ElMessage.success('已退出登录');
    drawer.value = false;
    
    // 退出登录后强制刷新主页数据
    console.log('🚪 用户退出登录，强制刷新主页数据');
    router.push({ path: '/', query: { _refresh: Date.now() } });
  } catch (error) {
    ElMessage.error('退出登录失败');
  }
}

// 处理头像加载错误
function handleAvatarError(e) {
  const img = e.target;
  img.style.display = 'none';
}

// 移动端汉堡菜单中的处理函数
function handleCategoryClick(categoryId) {
  router.push({ path: '/', query: { category_id: categoryId } });
  drawer.value = false;
}

function handleTagClick(tagSlug) {
  router.push({ path: '/', query: { tag: tagSlug } });
  drawer.value = false;
}

function handleArticleClick(articleSlug) {
  router.push(`/article/${articleSlug}`);
  drawer.value = false;
}

// 处理Logo点击 - 使用原生导航避免组件状态冲突
function handleLogoClick(e) {
  console.log('🏠 AppHeader: Logo点击，检查是否需要原生导航');
  
  // 检查当前路由是否为文章编辑页面
  const currentPath = router.currentRoute.value.path;
  const isOnNewArticlePage = currentPath === '/articles/new';
  
  if (isOnNewArticlePage) {
    console.log('🏠 AppHeader: 当前在文章编辑页面，使用原生导航避免VNode冲突');
    e.preventDefault();
    
    // 使用原生浏览器导航，完全绕过Vue Router
    window.location.href = '/';
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
function handleNavClick(path, e) {
  console.log(`🧭 AppHeader: 导航到 ${path}，检查是否需要原生导航`);
  
  // 检查当前路由是否为文章编辑页面
  const currentPath = router.currentRoute.value.path;
  const isOnNewArticlePage = currentPath === '/articles/new';
  
  if (isOnNewArticlePage) {
    console.log('🧭 AppHeader: 当前在文章编辑页面，使用原生导航避免VNode冲突');
    e.preventDefault();
    
    // 使用原生浏览器导航，完全绕过Vue Router
    window.location.href = path;
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

/* Logo hover 效果 */
.logo-container:hover .logo-icon {
  transform: scale(1.1);
  transition: transform 0.2s ease-in-out;
}

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
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
