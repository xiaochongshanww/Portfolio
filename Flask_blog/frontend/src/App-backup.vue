<template>
  <div>
    <h1>Simple Vue App Test</h1>
    <p>Current time: {{ new Date().toLocaleString() }}</p>
    <router-view />
  </div>
</template>

<script setup>
// 最简单的Vue组件测试
</script>

<style>
body {
  font-family: Arial, sans-serif;
  margin: 20px;
}
</style>