<template>
  <div class="p-8">
    <h1 class="text-2xl mb-4">图标测试页面</h1>
    
    <div class="mb-4">
      <h2 class="text-lg mb-2">直接使用图标组件：</h2>
      <div class="flex gap-4 items-center">
        <Document class="w-6 h-6" />
        <Reading class="w-6 h-6" />
        <Star class="w-6 h-6" />
        <TrendCharts class="w-6 h-6" />
      </div>
    </div>
    
    <div class="mb-4">
      <h2 class="text-lg mb-2">使用el-icon包装：</h2>
      <div class="flex gap-4 items-center">
        <el-icon size="24"><Document /></el-icon>
        <el-icon size="24"><Reading /></el-icon>
        <el-icon size="24"><Star /></el-icon>
        <el-icon size="24"><TrendCharts /></el-icon>
      </div>
    </div>

    <div class="mb-4">
      <h2 class="text-lg mb-2">使用component :is 方式：</h2>
      <div class="flex gap-4 items-center">
        <el-icon size="24"><component :is="'Document'" /></el-icon>
        <el-icon size="24"><component :is="'Reading'" /></el-icon>
        <el-icon size="24"><component :is="'Star'" /></el-icon>
        <el-icon size="24"><component :is="'TrendCharts'" /></el-icon>
      </div>
    </div>

    <div class="mb-4">
      <h2 class="text-lg mb-2">测试TagsPage中的视图切换器图标：</h2>
      <div class="flex gap-4 items-center">
        <button 
          v-for="view in viewModes" 
          :key="view.value"
          @click="currentView = view.value"
          :class="[
            'px-4 py-2 border rounded',
            currentView === view.value ? 'bg-blue-500 text-white' : 'bg-gray-100'
          ]"
        >
          <div class="flex items-center gap-2">
            <el-icon size="18"><component :is="view.icon" /></el-icon>
            <span>{{ view.label }}</span>
          </div>
        </button>
      </div>
    </div>

    <div class="mb-4">
      <h2 class="text-lg mb-2">测试其他TagsPage图标：</h2>
      <div class="flex gap-4 items-center">
        <el-icon size="24"><ArrowRight /></el-icon>
        <el-icon size="24"><Loading /></el-icon>
        <el-icon size="24" class="animate-spin"><Loading /></el-icon>
      </div>
    </div>

    <div class="mb-4">
      <h2 class="text-lg mb-2">调试信息：</h2>
      <pre>{{ debugInfo }}</pre>
    </div>
  </div>
</template>

<script setup>
import { computed, getCurrentInstance, ref } from 'vue'
import { Document, Reading, Star, TrendCharts, Compass, Grid, List, ArrowRight, Loading } from '@element-plus/icons-vue'

const instance = getCurrentInstance()

const viewModes = [
  { label: '标签云', value: 'cloud', icon: Compass },
  { label: '网格', value: 'grid', icon: Grid },
  { label: '列表', value: 'list', icon: List }
]

const currentView = ref('cloud')

const debugInfo = computed(() => {
  return {
    hasDocument: !!Document,
    hasReading: !!Reading,
    hasStar: !!Star,
    hasTrendCharts: !!TrendCharts,
    hasCompass: !!Compass,
    hasGrid: !!Grid,
    hasList: !!List,
    hasArrowRight: !!ArrowRight,
    hasLoading: !!Loading,
    globalComponents: Object.keys(instance?.appContext.components || {}).filter(name => 
      ['Document', 'Reading', 'Star', 'TrendCharts', 'Compass', 'Grid', 'List', 'ArrowRight', 'Loading'].includes(name)
    )
  }
})
</script>