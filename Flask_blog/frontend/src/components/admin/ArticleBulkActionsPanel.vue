<template>
  <div v-if="selectedCount > 0" class="modern-bulk-actions">
    <div class="bulk-decoration" />
    <div class="bulk-content">
      <div class="selected-info">
        <el-icon size="18"><Select /></el-icon>
        <span>已选择 <strong>{{ selectedCount }}</strong> 篇文章</span>
      </div>
      <div class="bulk-buttons">
        <button 
          v-if="canModerateContent" 
          class="bulk-btn success" 
          :disabled="!canBulkApprove"
          @click="emit('approve')"
        >
          <el-icon size="16"><Check /></el-icon>
          <span>批量审核通过</span>
        </button>
        <button 
          v-if="canModerateContent" 
          class="bulk-btn warning" 
          :disabled="!canBulkReject"
          @click="emit('reject')"
        >
          <el-icon size="16"><Close /></el-icon>
          <span>批量拒绝</span>
        </button>
        <button class="bulk-btn cancel" @click="emit('clear')">
          <el-icon size="16"><RefreshLeft /></el-icon>
          <span>取消选择</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Select, Check, Close, RefreshLeft } from '@element-plus/icons-vue';

defineProps({
  selectedCount: { type: Number, default: 0 },
  canModerateContent: { type: [Boolean, null], default: false },
  canBulkApprove: { type: Boolean, default: false },
  canBulkReject: { type: Boolean, default: false }
});

const emit = defineEmits(['approve', 'reject', 'clear']);
</script>

<style scoped>
/* 批量操作栏 */
.modern-bulk-actions {
  position: relative;
  margin-bottom: 1.5rem;
  background: 
    linear-gradient(135deg, 
      rgba(59, 130, 246, 0.08) 0%, 
      rgba(139, 92, 246, 0.05) 100%
    );
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  overflow: hidden;
  animation: slideInDown 0.3s ease-out;
}

@keyframes slideInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.bulk-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #06b6d4);
}

.bulk-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  position: relative;
  z-index: 2;
}

.selected-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #1e40af;
  font-size: 0.95rem;
}

.bulk-buttons {
  display: flex;
  gap: 0.75rem;
}

.bulk-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  border-radius: 10px;
  border: none;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.bulk-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.bulk-btn.success {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.05));
  color: #16a34a;
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.bulk-btn.success::before {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.05));
}

.bulk-btn.warning {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05));
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.bulk-btn.warning::before {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.05));
}

.bulk-btn.cancel {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.1), rgba(75, 85, 99, 0.05));
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.2);
}

.bulk-btn.cancel::before {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.1), rgba(75, 85, 99, 0.05));
}

.bulk-btn:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.bulk-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.bulk-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.bulk-btn:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .bulk-content {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
  
  .bulk-buttons {
    justify-content: center;
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  .bulk-buttons {
    flex-direction: column;
    width: 100%;
  }
  
  .bulk-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
