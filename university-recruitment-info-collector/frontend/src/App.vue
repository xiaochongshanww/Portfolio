<template>
  <div class="app-shell min-h-screen flex flex-col">
    <div class="app-orb app-orb-a"></div>
    <div class="app-orb app-orb-b"></div>
    <div class="app-grid"></div>

    <header class="sticky top-0 z-50 px-4 pt-4 sm:px-6 lg:px-8">
      <div class="shell-frame mx-auto max-w-7xl px-4 py-4 sm:px-6">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div class="min-w-0">
            <p class="section-kicker">University Recruitment Intelligence</p>
            <div class="mt-1 flex flex-wrap items-center gap-3">
              <h1 class="text-xl font-semibold text-slate-950 sm:text-2xl">高校招聘信息采集与匹配</h1>
              <span class="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
                <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
                招聘数据与智能匹配联动
              </span>
            </div>
            <p class="mt-2 max-w-2xl text-sm text-slate-500">
              面向广州高校岗位，统一查看岗位质量、原文来源与个人画像匹配结果。
            </p>
          </div>

          <nav class="nav-pills flex flex-wrap gap-2">
            <router-link to="/jobs" class="nav-pill" :class="{ 'nav-pill-active': route.path === '/jobs' }">
              岗位总览
            </router-link>
            <router-link to="/profile" class="nav-pill" :class="{ 'nav-pill-active': route.path === '/profile' || route.path === '/match' }">
              画像与匹配
            </router-link>
          </nav>
        </div>
      </div>
    </header>

    <main class="relative z-10 flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div class="mx-auto max-w-7xl">
        <router-view />
      </div>
    </main>

    <footer class="relative z-10 px-4 pb-6 sm:px-6 lg:px-8">
      <div class="shell-frame mx-auto max-w-7xl px-4 py-4 text-sm text-slate-500 sm:px-6">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <span>数据来源：各高校人事官网与招聘聚合站点</span>
          <span>采集、质量评估、匹配推荐一体化工作台</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>
