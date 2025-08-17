<template>
  <div class="min-h-screen bg-slate-50 text-gray-800">
    <!-- 固定在顶部的Header - 全屏渐变背景 -->
    <header 
      class="header-gradient-bg fixed top-0 left-0 right-0 z-50 transition-all duration-300 w-full"
      :class="{ 'header-scrolled': isScrolled }"
      :style="{ 
        paddingTop: '1rem',
        paddingBottom: '0.5rem'
      }"
    >
      <!-- 居中的容器 -->
      <div class="container">
        <AppHeader :is-scrolled="isScrolled" :sidebar-data="sidebarData" />
      </div>
    </header>
    
    <!-- 主要内容区域 - 添加顶部边距避免被Header遮挡 -->
    <div class="container-content">
      <main class="bg-white rounded-lg shadow-sm">
        <div class="p-6">
          <router-view />
        </div>
      </main>
      
      <AppFooter />
    </div>
    <GlobalNotify />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, provide } from 'vue';
import GlobalNotify from './components/GlobalNotify.vue';
import AppFooter from './components/layout/AppFooter.vue';
import AppHeader from './components/layout/AppHeader.vue';
import { useSessionStore } from './stores/session';

const isScrolled = ref(false);
const sidebarData = ref({
  categories: [],
  tags: [],
  hotArticles: []
});

const session = useSessionStore();

// 滚动检测
function handleScroll() {
  isScrolled.value = window.scrollY > 10;
}

// 提供侧边栏数据给子组件
provide('sidebarData', sidebarData);

onMounted(async () => {
  window.addEventListener('scroll', handleScroll);
  
  // 恢复用户登录状态
  if (session.token && !session.user) {
    try {
      await session.fetchUserInfo();
    } catch (error) {
      console.log('恢复用户状态失败:', error);
    }
  }
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<style>
/* 页头渐变背景效果 */
.header-gradient-bg {
  background: linear-gradient(
    180deg, 
    rgba(255, 255, 255, 1) 0%,     /* 顶部完全白色 */
    rgba(255, 255, 255, 0.95) 30%, /* 上部稍微透明 */
    rgba(255, 255, 255, 0.85) 60%, /* 中部更透明 */
    rgba(255, 255, 255, 0.7) 90%,  /* 下部明显淡出 */
    rgba(255, 255, 255, 0.6) 100%  /* 底部最大淡出 */
  );
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
}

/* 滚动时增强效果 */
.header-gradient-bg.header-scrolled {
  background: linear-gradient(
    180deg, 
    rgba(255, 255, 255, 1) 0%,     /* 滚动时顶部保持完全白色 */
    rgba(255, 255, 255, 0.98) 30%, /* 上部稍微增强 */
    rgba(255, 255, 255, 0.92) 60%, /* 中部增强 */
    rgba(255, 255, 255, 0.8) 90%,  /* 下部增强 */
    rgba(255, 255, 255, 0.75) 100% /* 底部增强 */
  );
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

/* 全局样式重置和优化 */
html, body {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

*, *::before, *::after {
  box-sizing: inherit;
}

/* Element Plus 组件样式覆盖 */
.el-menu {
  border-right: none !important;
}

/* 确保页面布局正确 */
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 主内容区域 */
main {
  flex: 1;
  min-height: 0; /* 防止 flex 项目溢出 */
}

/* 阶梯式响应式容器系统 - 参考优秀网站实现 */
.container {
  width: 100% !important;
  margin: 0 auto !important;
  padding: 0 1rem !important;
  display: block !important;
}

/* 页头容器的阶梯式max-width */
@media (min-width: 576px) { .container { max-width: 540px !important; } }
@media (min-width: 768px) { .container { max-width: 720px !important; } }
@media (min-width: 992px) { .container { max-width: 960px !important; } }
@media (min-width: 1200px) { .container { max-width: 1140px !important; } }
@media (min-width: 1400px) { .container { max-width: 1320px !important; } }

/* 内容区域容器 - 与页头保持一致的阶梯式响应 */
.container-content {
  width: 100%;
  margin: 0 auto;
  padding: 8rem 1rem 2rem 1rem; /* 8rem 顶部边距用于避开固定头部 */
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* 内容容器的阶梯式max-width（与页头保持一致）*/
@media (min-width: 576px) { .container-content { max-width: 540px; } }
@media (min-width: 768px) { .container-content { max-width: 720px; } }
@media (min-width: 992px) { .container-content { max-width: 960px; } }
@media (min-width: 1200px) { .container-content { max-width: 1140px; } }
@media (min-width: 1400px) { .container-content { max-width: 1320px; } }

/* 移动端响应式调整 */
@media (max-width: 768px) {
  .container {
    width: 95%;
    padding: 0 0.5rem;
  }
  
  .container-content {
    width: 95%;
    padding: 6.5rem 0.5rem 1rem 0.5rem;
    gap: 0.5rem;
  }
}

@media (max-width: 480px) {
  .container {
    width: 98%;
    padding: 0 0.25rem;
  }
  
  .container-content {
    width: 98%;
    padding: 6rem 0.25rem 1rem 0.25rem;
  }
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f5f9;
}

::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
