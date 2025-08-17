<template>
  <div class="rounded-lg shadow-sm transition-all duration-300" 
    :class="{ 'shadow-md': isScrolled }"
    ref="headerRef"
  >
    <div class="px-6 py-4">
      <div class="flex justify-between items-center w-full">
        <!-- Logo -->
        <div class="flex-shrink-0">
          <router-link 
            to="/" 
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
          </router-link>
        </div>

        <!-- Desktop Navigation -->
        <nav class="desktop-nav items-center space-x-8 flex-1 justify-center">
          <router-link 
            to="/" 
            class="nav-link"
            :class="{ 'nav-link-active': $route.path === '/' }"
          >
            <el-icon class="mr-1"><HomeFilled /></el-icon>
            主页
          </router-link>
          <router-link 
            to="/categories" 
            class="nav-link"
            :class="{ 'nav-link-active': $route.path.startsWith('/category') }"
          >
            <el-icon class="mr-1"><Collection /></el-icon>
            分类浏览
          </router-link>
          <router-link 
            to="/hot" 
            class="nav-link"
            :class="{ 'nav-link-active': $route.path === '/hot' }"
          >
            <el-icon class="mr-1"><TrendCharts /></el-icon>
            热门
          </router-link>
          <router-link 
            to="/about" 
            class="nav-link"
            :class="{ 'nav-link-active': $route.path === '/about' }"
          >
            <el-icon class="mr-1"><InfoFilled /></el-icon>
            关于
          </router-link>
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
            <router-link 
              to="/articles/new"
              class="inline-flex items-center px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
            >
              <el-icon class="mr-1"><EditPen /></el-icon>
              写文章
            </router-link>

            <!-- 用户头像下拉菜单 -->
            <el-dropdown @command="handleCommand" trigger="click">
              <div class="flex items-center cursor-pointer hover:bg-gray-50 rounded-lg p-1.5 transition-colors">
                <div class="w-8 h-8 rounded-full overflow-hidden bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center">
                  <img 
                    v-if="me.avatar" 
                    :src="me.avatar" 
                    :alt="me.nickname || me.email"
                    class="w-full h-full object-cover"
                    @error="handleAvatarError"
                  />
                  <el-icon v-else class="text-white text-sm"><User /></el-icon>
                </div>
                <div class="ml-2 text-sm">
                  <div class="font-medium text-gray-900">{{ me.nickname || '用户' }}</div>
                </div>
                <el-icon class="ml-1 text-gray-400"><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="`/author/${me.id}`" v-if="me.id">
                    <el-icon><User /></el-icon>
                    个人主页
                  </el-dropdown-item>
                  <el-dropdown-item command="/me/profile">
                    <el-icon><Setting /></el-icon>
                    设置
                  </el-dropdown-item>
                  <el-dropdown-item divided v-if="me.role === 'editor' || me.role === 'admin'">
                    管理功能
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
              <div class="font-medium text-gray-900">{{ me.nickname || '用户' }}</div>
              <div class="text-sm text-gray-500">{{ me.email }}</div>
            </div>
          </div>
        </div>

        <!-- 移动端导航 -->
        <div class="flex-1 py-4">
          <nav class="space-y-1">
            <router-link 
              to="/" 
              @click="drawer = false" 
              class="mobile-nav-link"
              :class="{ 'mobile-nav-link-active': $route.path === '/' }"
            >
              <el-icon class="mr-3"><HomeFilled /></el-icon>
              主页
            </router-link>
            
            <router-link 
              to="/categories" 
              @click="drawer = false" 
              class="mobile-nav-link"
            >
              <el-icon class="mr-3"><Collection /></el-icon>
              分类浏览
            </router-link>
            
            <router-link 
              to="/hot" 
              @click="drawer = false" 
              class="mobile-nav-link"
            >
              <el-icon class="mr-3"><TrendCharts /></el-icon>
              热门
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
import { useSessionStore } from '../../stores/session';
import { ElMessage } from 'element-plus';
import {
  User, EditPen, ArrowDown, Setting, Collection, UserFilled, DataAnalysis,
  SwitchButton, Menu, HomeFilled, TrendCharts, InfoFilled
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
const session = useSessionStore();
const { user: me } = storeToRefs(session);
const headerRef = ref(null);

// 从props获取侧边栏数据
const sidebarCategories = computed(() => props.sidebarData?.categories?.slice(0, 6) || []);
const sidebarTags = computed(() => props.sidebarData?.tags?.slice(0, 8) || []);
const hotArticles = computed(() => props.sidebarData?.hotArticles?.slice(0, 3) || []);

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
    await session.logout();
    ElMessage.success('已退出登录');
    drawer.value = false;
    router.push('/');
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

/* 移动端抽屉样式 */
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

/* line-clamp utilities */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
