<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo / Title -->
          <div class="flex items-center gap-3">
            <span class="text-xl font-bold text-blue-600 tracking-tight">🎓 高校招聘信息采集与匹配</span>
          </div>
          <!-- Navigation -->
          <el-menu
            :default-active="$route.path"
            mode="horizontal"
            :ellipsis="false"
            router
            class="border-none! bg-transparent! flex-1 justify-end"
          >
            <el-menu-item index="/jobs">
              <span class="text-base">📋 岗位列表</span>
            </el-menu-item>
            <el-menu-item index="/profile">
              <span class="text-base">👤 我的画像</span>
            </el-menu-item>
          </el-menu>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <router-view />
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-gray-200 py-4 mt-auto">
      <div class="max-w-7xl mx-auto px-4 text-center text-sm text-gray-400">
        高校招聘信息采集与匹配 · 数据来源：各高校人事处官网 & 高校人才网
      </div>
    </footer>
  </div>
</template>

<script setup>
</script>
