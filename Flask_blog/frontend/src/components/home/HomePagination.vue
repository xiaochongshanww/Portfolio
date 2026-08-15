<template>
  <div class="pagination-container">
    <el-pagination
      background
      layout="prev, pager, next, sizes, total"
      :page-sizes="[10,20,50]"
      :default-page-size="10"
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      @current-change="$emit('page-change', $event)"
      @size-change="$emit('size-change', $event)"
    />
  </div>
</template>

<script setup>
defineProps({
  total: {
    type: Number,
    default: 0
  },
  page: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 10
  }
});

defineEmits(['page-change', 'size-change']);
</script>

<style scoped>
/* 翻页组件独立容器 - 确保固定在底部并与内容分离 */
.pagination-container {
  margin-top: 4rem; /* 与内容区域保持固定间距 */
  margin-bottom: 2rem;
  padding-top: 2rem;
  padding-bottom: 1rem;
  display: flex;
  justify-content: center;
  border-top: 1px solid #f1f5f9; /* 添加分隔线 */
  background: rgba(255, 255, 255, 0.8); /* 轻微背景色区分 */
  backdrop-filter: blur(8px); /* 毛玻璃效果 */
  border-radius: 16px;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05); /* 轻微阴影 */
}
</style>
