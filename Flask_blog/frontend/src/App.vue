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
    
    <!-- 回到顶部按钮 -->
    <ScrollToTop />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, provide } from 'vue';
import GlobalNotify from './components/GlobalNotify.vue';
import AppFooter from './components/layout/AppFooter.vue';
import AppHeader from './components/layout/AppHeader.vue';
import ScrollToTop from './components/ScrollToTop.vue';
import { useUserStore } from './stores/user';

const isScrolled = ref(false);
const sidebarData = ref({
  categories: [],
  tags: [],
  hotArticles: []
});

const userStore = useUserStore();

// 滚动检测
function handleScroll() {
  isScrolled.value = window.scrollY > 10;
}

// 提供侧边栏数据给子组件
provide('sidebarData', sidebarData);

onMounted(async () => {
  window.addEventListener('scroll', handleScroll);
  
  // 初始化用户认证状态
  try {
    await userStore.initAuth();
  } catch (error) {
    console.log('初始化用户状态失败:', error);
  }
  
  // 添加全局消息点击关闭功能
  setupMessageClickHandlers();
});

// 设置消息点击处理器
function setupMessageClickHandlers() {
  // 使用事件委托监听消息点击
  document.addEventListener('click', (event) => {
    const messageElement = event.target.closest('.enhanced-message');
    if (messageElement) {
      // 检查是否点击的是关闭按钮，如果是则让默认行为处理
      const closeBtn = event.target.closest('.el-message__closeBtn');
      if (closeBtn) {
        return; // 让默认关闭按钮处理
      }
      
      // 点击消息卡片其他区域时关闭消息
      const closeButton = messageElement.querySelector('.el-message__closeBtn');
      if (closeButton) {
        closeButton.click();
      } else {
        // 如果没有关闭按钮，尝试直接关闭
        messageElement.style.opacity = '0';
        messageElement.style.transform = 'translateY(-20px) scale(0.9)';
        setTimeout(() => {
          messageElement.remove();
        }, 300);
      }
    }
  });
}

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

/* 增强的消息样式 - 高对比度设计 + 点击体验 */
.enhanced-message {
  border-radius: 16px !important;
  box-shadow: 
    0 20px 40px rgba(0, 0, 0, 0.15), 
    0 8px 16px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  line-height: 1.6 !important;
  padding: 20px 24px !important;
  margin-bottom: 16px !important;
  position: relative !important;
  z-index: 3000 !important;
  backdrop-filter: blur(12px) saturate(180%) !important;
  border: 2px solid !important;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
  min-height: 60px !important;
  display: flex !important;
  align-items: center !important;
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8) !important;
  cursor: pointer !important;
  user-select: none !important;
}

.enhanced-message:hover {
  transform: translateY(-4px) scale(1.02) !important;
  box-shadow: 
    0 25px 50px rgba(0, 0, 0, 0.2), 
    0 12px 24px rgba(0, 0, 0, 0.15),
    0 0 0 1px rgba(255, 255, 255, 0.2) inset !important;
}

/* 点击效果 */
.enhanced-message:active {
  transform: translateY(-2px) scale(1.01) !important;
  box-shadow: 
    0 15px 35px rgba(0, 0, 0, 0.15), 
    0 6px 12px rgba(0, 0, 0, 0.1),
    0 0 0 1px rgba(255, 255, 255, 0.15) inset !important;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* 不同类型消息的特定样式 - 高对比度背景 */
.enhanced-message.el-message--success {
  background: linear-gradient(135deg, 
    rgba(16, 185, 129, 0.95) 0%, 
    rgba(5, 150, 105, 0.9) 50%,
    rgba(4, 120, 87, 0.95) 100%) !important;
  border-color: rgba(16, 185, 129, 0.8) !important;
  color: #ffffff !important;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
}

.enhanced-message.el-message--error {
  background: linear-gradient(135deg, 
    rgba(239, 68, 68, 0.95) 0%, 
    rgba(220, 38, 38, 0.9) 50%,
    rgba(185, 28, 28, 0.95) 100%) !important;
  border-color: rgba(239, 68, 68, 0.8) !important;
  color: #ffffff !important;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
}

.enhanced-message.el-message--warning {
  background: linear-gradient(135deg, 
    rgba(245, 158, 11, 0.95) 0%, 
    rgba(217, 119, 6, 0.9) 50%,
    rgba(180, 83, 9, 0.95) 100%) !important;
  border-color: rgba(245, 158, 11, 0.8) !important;
  color: #ffffff !important;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
}

.enhanced-message.el-message--info {
  background: linear-gradient(135deg, 
    rgba(59, 130, 246, 0.95) 0%, 
    rgba(37, 99, 235, 0.9) 50%,
    rgba(29, 78, 216, 0.95) 100%) !important;
  border-color: rgba(59, 130, 246, 0.8) !important;
  color: #ffffff !important;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
}

/* 消息图标样式 */
.enhanced-message .el-message__icon {
  font-size: 22px !important;
  margin-right: 16px !important;
  color: rgba(255, 255, 255, 0.95) !important;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
  filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.5)) !important;
}

/* 关闭按钮样式 */
.enhanced-message .el-message__closeBtn {
  font-size: 18px !important;
  color: rgba(255, 255, 255, 0.8) !important;
  background: rgba(0, 0, 0, 0.2) !important;
  border-radius: 50% !important;
  width: 28px !important;
  height: 28px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: all 0.3s ease !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
}

.enhanced-message .el-message__closeBtn:hover {
  background: rgba(255, 255, 255, 0.2) !important;
  color: #ffffff !important;
  transform: scale(1.15) rotate(90deg) !important;
  border-color: rgba(255, 255, 255, 0.6) !important;
}

/* 确保消息容器在正确的层级 */
.el-message {
  position: fixed !important;
  top: 90px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  z-index: 3000 !important;
  min-width: 380px !important;
  max-width: 600px !important;
  animation: slideInDown 0.5s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* 消息入场动画 */
@keyframes slideInDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0) scale(1);
  }
}

/* 消息文本内容样式 */
.enhanced-message .el-message__content {
  font-weight: 600 !important;
  letter-spacing: 0.02em !important;
  word-break: break-word !important;
}

/* 添加消息背景遮罩层（可选） */
.enhanced-message::before {
  content: '' !important;
  position: absolute !important;
  top: -10px !important;
  left: -10px !important;
  right: -10px !important;
  bottom: -10px !important;
  background: radial-gradient(ellipse at center, 
    rgba(0, 0, 0, 0.1) 0%, 
    transparent 70%) !important;
  border-radius: 24px !important;
  z-index: -1 !important;
  opacity: 0.6 !important;
}

/* 点击提示文本 */
.enhanced-message::after {
  content: '点击关闭' !important;
  position: absolute !important;
  bottom: 8px !important;
  right: 16px !important;
  font-size: 11px !important;
  opacity: 0.7 !important;
  font-weight: 400 !important;
  letter-spacing: 0.5px !important;
  pointer-events: none !important;
  transition: opacity 0.3s ease !important;
}

.enhanced-message:hover::after {
  opacity: 0.9 !important;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .enhanced-message {
    margin: 0 16px !important;
    padding: 18px 20px !important;
    font-size: 14px !important;
    min-width: auto !important;
    max-width: calc(100vw - 32px) !important;
    min-height: 56px !important;
  }
  
  .enhanced-message .el-message__icon {
    font-size: 20px !important;
    margin-right: 14px !important;
  }
  
  .enhanced-message .el-message__closeBtn {
    width: 26px !important;
    height: 26px !important;
    font-size: 16px !important;
  }
  
  .el-message {
    top: 80px !important;
    left: 16px !important;
    right: 16px !important;
    transform: none !important;
    width: auto !important;
    min-width: auto !important;
    max-width: none !important;
  }
  
  /* 移动端点击提示调整 */
  .enhanced-message::after {
    font-size: 10px !important;
    bottom: 6px !important;
    right: 12px !important;
  }
}

/* 高对比度和辅助功能支持 */
@media (prefers-contrast: high) {
  .enhanced-message {
    border-width: 3px !important;
    box-shadow: 0 0 0 2px #000000 !important;
  }
  
  /* 高对比度模式下的点击提示 */
  .enhanced-message::after {
    opacity: 1 !important;
    font-weight: 600 !important;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8) !important;
  }
}

/* 减少动画（如果用户偏好） */
@media (prefers-reduced-motion: reduce) {
  .enhanced-message,
  .enhanced-message .el-message__closeBtn {
    transition: none !important;
    animation: none !important;
  }
  
  .enhanced-message:hover {
    transform: none !important;
  }
}

/* 退出成功对话框样式 */
.logout-success-dialog {
  border-radius: 20px !important;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15) !important;
  border: none !important;
  overflow: hidden !important;
}

.logout-success-dialog .el-message-box__header {
  padding: 24px 24px 0 !important;
  border-bottom: none !important;
}

.logout-success-dialog .el-message-box__title {
  font-size: 24px !important;
  font-weight: 700 !important;
  color: #6366f1 !important;
  text-align: center !important;
}

.logout-success-dialog .el-message-box__content {
  padding: 0 24px 24px !important;
}

.logout-success-dialog .el-message-box__message {
  margin: 0 !important;
  color: inherit !important;
}

/* 退出成功对话框的背景遮罩 */
.logout-success-dialog + .el-overlay {
  background-color: rgba(0, 0, 0, 0.6) !important;
  backdrop-filter: blur(8px) !important;
}
</style>
