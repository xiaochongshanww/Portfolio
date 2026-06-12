<template>
  <el-container style="min-height: 100vh">
    <el-header style="background: #409eff; color: #fff; display: flex; align-items: center; padding: 0 20px;">
      <h2 style="margin: 0; font-size: 18px;">高校招聘信息采集与匹配</h2>
      <el-menu
        :default-active="$route.path"
        mode="horizontal"
        style="margin-left: 40px; background: transparent; border: none;"
        router
      >
        <el-menu-item index="/jobs" style="color: #fff; border: none;">岗位列表</el-menu-item>
        <el-menu-item index="/profile" style="color: #fff; border: none;">我的画像</el-menu-item>
      </el-menu>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
</script>
