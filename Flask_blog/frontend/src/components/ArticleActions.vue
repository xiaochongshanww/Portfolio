<template>
  <div v-if="isModerator && (nextList.length || canSchedule || canUnschedule || canUnpublish)" class="admin-actions">
    <div class="admin-actions-content">
      <span class="admin-actions-label">管理操作:</span>
      <div class="admin-actions-buttons">
        <el-button v-for="n in nextList" :key="n" :disabled="acting || !canOperate(n)" size="small" @click="emit('transition', n)">{{ n }}</el-button>
        <el-button v-if="canSchedule" :disabled="acting" size="small" @click="emit('schedule')">定时发布</el-button>
        <el-button v-if="canUnschedule" :disabled="acting" size="small" @click="emit('unschedule')">取消定时</el-button>
        <el-button v-if="canUnpublish" :disabled="acting" size="small" type="warning" @click="emit('unpublish')">下线</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  isModerator: boolean
  nextList: string[]
  canSchedule: boolean
  canUnschedule: boolean
  canUnpublish: boolean
  acting: boolean
  canOperate: (target: string) => boolean
}>()

const emit = defineEmits<{
  transition: [target: string]
  schedule: []
  unschedule: []
  unpublish: []
}>()
</script>

<style scoped>
.admin-actions {
  margin: 0 3rem 2rem;
  padding: 1rem 1.5rem;
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  border: 1px solid #f59e0b;
  border-radius: 12px;
}

.admin-actions-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.admin-actions-label {
  font-weight: 600;
  color: #92400e;
}

.admin-actions-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
