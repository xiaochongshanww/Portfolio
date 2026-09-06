<template>
  <!-- Admin 壳(04 V2 §1/§2):/admin/* 视口级应用壳,AdminLayout 自持布局,
       不渲染 PublicHeader/Footer 或 max-width 容器 -->
  <router-view v-if="isAdminShell" />

  <!-- 公共站壳:暖纸底 + PublicHeader/Footer(meta.public 路由) -->
  <div v-else-if="isPublicShell" class="public-shell">
    <PublicHeader />
    <main class="public-main">
      <router-view />
    </main>
    <PublicFooter />
    <SearchOverlay />
    <GlobalNotify />
    <ScrollToTop />
  </div>

</template>

<script setup>
// App 根组件:仅负责壳分发——admin 壳(/admin/*)与公共 V2 壳(meta.public),
// legacy 壳已随旧页面退役移除(壳归一阶段 1)。
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useUserStore } from './stores/user';
import PublicHeader from './components/public/PublicHeader.vue';
import PublicFooter from './components/public/PublicFooter.vue';
import SearchOverlay from './components/public/SearchOverlay.vue';
import ScrollToTop from './components/ScrollToTop.vue';
import GlobalNotify from './components/GlobalNotify.vue';

// 注意:本构建的 Tailwind 工具类未生成(v4 迁移遗留),所有壳层样式均为实样式
const route = useRoute();
const userStore = useUserStore();

// 04 V2 §2:/admin/* 使用独立 Layout,顶层只渲染 router-view
const isAdminShell = computed(() => route.path.startsWith('/admin'));
const isPublicShell = computed(() => route.meta?.public === true);

onMounted(async () => {
  // 初始化用户认证状态
  try {
    await userStore.initAuth();
  } catch (error) {
    console.error('初始化用户状态失败:', error);
  }
});
</script>


<style>
/* ===== 公共站壳(P0-B3,壳归一后保留的唯一样式区)===== */
.public-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
}
.public-main {
  flex: 1;
}

/* 全局基础 */
html, body {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
*, *::before, *::after {
  box-sizing: inherit;
}
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
main {
  flex: 1;
  min-height: 0;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: var(--surface-2, #f1f1ee);
}
::-webkit-scrollbar-thumb {
  background: var(--line-strong, #d4d4ce);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--muted, #6b6b67);
}
</style>
