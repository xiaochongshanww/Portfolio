<template>
  <div class="schedule-picker">
    <el-form-item label="定时发布">
      <div class="schedule-row">
        <el-switch
          :model-value="enabled"
          @update:model-value="onToggle"
          active-text="启用定时发布"
          class="schedule-switch"
        />
        <el-date-picker
          v-if="enabled"
          :model-value="date"
          @update:model-value="$emit('update:date', $event)"
          type="datetime"
          placeholder="选择发布时间"
          :disabled-date="disabledDate"
          class="schedule-datepicker"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DDTHH:mm:ss"
        />
      </div>
    </el-form-item>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  enabled: boolean
  date: string
}>()

const emit = defineEmits<{
  'update:enabled': [value: boolean]
  'update:date': [value: string]
}>()

function onToggle(val: boolean) {
  emit('update:enabled', val)
  if (!val) {
    emit('update:date', '')
  }
}

function disabledDate(time: Date): boolean {
  return time.getTime() < Date.now() - 86400000
}
</script>

<style scoped>
.schedule-row {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}
.schedule-switch {
  flex-shrink: 0;
}
.schedule-datepicker {
  flex: 1;
}
</style>
