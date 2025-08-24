<template>
  <div class="comment-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">评论管理</h1>
        <p class="page-description">审核和管理用户评论，维护社区讨论质量</p>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-label">待审核</span>
          <span class="stat-value pending">{{ stats.pending }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">今日评论</span>
          <span class="stat-value">{{ stats.today }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">总评论</span>
          <span class="stat-value">{{ stats.total }}</span>
        </div>
      </div>
    </div>

    <!-- 筛选和搜索 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-group">
          <el-select v-model="filters.status" placeholder="状态筛选" clearable @change="loadComments">
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
          
          <el-input
            v-model="filters.article_id"
            placeholder="文章ID筛选"
            clearable
            @keyup.enter="loadComments"
            @clear="loadComments"
          />
          
          <el-input
            v-model="filters.content"
            placeholder="评论内容搜索"
            clearable
            @keyup.enter="loadComments"
            @clear="loadComments"
          />
        </div>
        
        <div class="action-group">
          <el-button @click="loadComments" :loading="loading" :icon="Refresh">刷新</el-button>
          <el-button 
            type="danger" 
            :disabled="selectedComments.length === 0"
            @click="handleBatchAction('reject')"
            :icon="Delete"
          >
            批量拒绝 ({{ selectedComments.length }})
          </el-button>
          <el-button 
            type="success" 
            :disabled="selectedComments.length === 0"
            @click="handleBatchAction('approve')"
            :icon="Check"
          >
            批量通过 ({{ selectedComments.length }})
          </el-button>
        </div>
      </div>
    </div>

    <!-- 评论列表 -->
    <div class="comments-table">
      <el-table
        v-loading="loading"
        :data="comments"
        @selection-change="handleSelectionChange"
        row-key="id"
        size="default"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="id" label="ID" width="80" sortable />
        
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <div :class="['modern-status-badge', row.status]">
              <div class="status-indicator">
                <el-icon size="14">
                  <Clock v-if="row.status === 'pending'" />
                  <Check v-else-if="row.status === 'approved'" />
                  <Close v-else-if="row.status === 'rejected'" />
                </el-icon>
                <span class="status-text">{{ getStatusText(row.status) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="content" label="评论内容" min-width="300">
          <template #default="{ row }">
            <div class="comment-content">
              <p>{{ row.content }}</p>
              <div class="comment-meta">
                <span>
                  <el-icon size="12"><Document /></el-icon>
                  文章ID: {{ row.article_id }}
                </span>
                <span v-if="row.parent_id">
                  <el-icon size="12"><ChatLineRound /></el-icon>
                  回复ID: {{ row.parent_id }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="user_id" label="用户ID" width="100">
          <template #default="{ row }">
            <div class="user-id-display">
              <el-icon size="14"><User /></el-icon>
              <span>{{ row.user_id }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="发表时间" width="180">
          <template #default="{ row }">
            <div class="time-display">
              <el-icon size="14"><Clock /></el-icon>
              <span>{{ formatDate(row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="modern-action-buttons">
              <button
                v-if="row.status === 'pending'"
                @click="handleModerate(row, 'approve')"
                :disabled="moderatingIds.has(row.id)"
                class="table-btn approve"
              >
                <el-icon size="14" :class="{ 'is-loading': moderatingIds.has(row.id) }"><Check /></el-icon>
                <span>通过</span>
              </button>
              
              <button
                v-if="row.status === 'pending'"
                @click="handleModerate(row, 'reject')"
                :disabled="moderatingIds.has(row.id)"
                class="table-btn reject"
              >
                <el-icon size="14" :class="{ 'is-loading': moderatingIds.has(row.id) }"><Close /></el-icon>
                <span>拒绝</span>
              </button>
              
              <button
                v-if="row.status === 'approved'"
                @click="handleModerate(row, 'reject')"
                :disabled="moderatingIds.has(row.id)"
                class="table-btn revoke"
              >
                <el-icon size="14" :class="{ 'is-loading': moderatingIds.has(row.id) }"><Hide /></el-icon>
                <span>撤销</span>
              </button>
              
              <button
                v-if="row.status === 'rejected'"
                @click="handleModerate(row, 'approve')"
                :disabled="moderatingIds.has(row.id)"
                class="table-btn restore"
              >
                <el-icon size="14" :class="{ 'is-loading': moderatingIds.has(row.id) }"><Refresh /></el-icon>
                <span>恢复</span>
              </button>
              
              <button
                @click="viewArticle(row.article_id)"
                class="table-btn view"
              >
                <el-icon size="14"><View /></el-icon>
                <span>查看文章</span>
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper" v-if="pagination.total > 0">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="loadComments"
        @size-change="loadComments"
      />
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && comments.length === 0" class="empty-state">
      <el-empty description="暂无评论数据">
        <el-button @click="loadComments">重新加载</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useRouter } from 'vue-router';
import api from '../../apiClient';
import { 
  ChatLineRound, Clock, Calendar, DataBoard, Document, Search, 
  Refresh, Delete, Check, Close, Hide, View, User 
} from '@element-plus/icons-vue';

const router = useRouter();

// 响应式数据
const loading = ref(false);
const comments = ref([]);
const selectedComments = ref([]);
const moderatingIds = ref(new Set());

// 统计数据
const stats = reactive({
  pending: 0,
  today: 0,
  total: 0
});

// 筛选器
const filters = reactive({
  status: '',
  article_id: '',
  content: ''
});

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
});

// 加载评论列表
const loadComments = async () => {
  if (loading.value) return;
  
  try {
    loading.value = true;
    
    // 构建请求参数
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    };
    
    // 添加筛选参数
    if (filters.status) params.status = filters.status;
    if (filters.article_id) params.article_id = filters.article_id;
    if (filters.content) params.content = filters.content;
    
    const response = await api.get('/comments/admin/list', { params });
    
    if (response.data.code === 0) {
      const data = response.data.data;
      comments.value = data.list || [];
      pagination.total = data.total || 0;
      
      // 更新统计
      await loadStats();
    } else {
      ElMessage.error(response.data.message || '加载评论失败');
    }
  } catch (error) {
    console.error('加载评论失败:', error);
    ElMessage.error('加载评论失败');
  } finally {
    loading.value = false;
  }
};

// 加载统计数据
const loadStats = async () => {
  try {
    const response = await api.get('/comments/admin/stats');
    if (response.data.code === 0) {
      Object.assign(stats, response.data.data);
    }
  } catch (error) {
    console.error('加载统计数据失败:', error);
  }
};

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedComments.value = selection;
};

// 单个审核操作
const handleModerate = async (comment, action) => {
  if (moderatingIds.value.has(comment.id)) return;
  
  try {
    moderatingIds.value.add(comment.id);
    
    const response = await api.post(`/comments/moderate/${comment.id}`, {
      action
    });
    
    if (response.data.code === 0) {
      ElMessage.success(
        action === 'approve' ? '评论已通过' : '评论已拒绝'
      );
      
      // 更新本地数据
      comment.status = action === 'approve' ? 'approved' : 'rejected';
      
      // 重新加载统计
      await loadStats();
    } else {
      ElMessage.error(response.data.message || '操作失败');
    }
  } catch (error) {
    console.error('审核失败:', error);
    ElMessage.error('审核失败');
  } finally {
    moderatingIds.value.delete(comment.id);
  }
};

// 批量操作
const handleBatchAction = async (action) => {
  if (selectedComments.value.length === 0) return;
  
  const actionText = action === 'approve' ? '通过' : '拒绝';
  
  try {
    await ElMessageBox.confirm(
      `确定要批量${actionText}所选的 ${selectedComments.value.length} 条评论吗？`,
      '批量操作确认',
      {
        type: 'warning',
        confirmButtonText: `确定${actionText}`,
        cancelButtonText: '取消'
      }
    );
    
    const ids = selectedComments.value.map(c => c.id);
    
    // 使用批量API
    const response = await api.post('/comments/moderate/batch', {
      ids,
      action
    });
    
    if (response.data.code === 0) {
      ElMessage.success(`批量${actionText}操作完成，更新了 ${response.data.data.updated_count} 条评论`);
      
      // 更新本地数据
      const new_status = response.data.data.status;
      selectedComments.value.forEach(selected => {
        const comment = comments.value.find(c => c.id === selected.id);
        if (comment) {
          comment.status = new_status;
        }
      });
      
      // 清除选择并重新加载统计
      selectedComments.value = [];
      await loadStats();
    } else {
      ElMessage.error(response.data.message || '批量操作失败');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量操作失败:', error);
      ElMessage.error(`批量${actionText}失败`);
    }
  }
};

// 查看文章
const viewArticle = (articleId) => {
  const url = router.resolve({ name: 'ArticleDetail', params: { id: articleId } }).href;
  window.open(url, '_blank');
};

// 格式化日期
const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 获取状态样式
const getStatusType = (status) => {
  switch (status) {
    case 'pending': return 'warning';
    case 'approved': return 'success';
    case 'rejected': return 'danger';
    default: return 'info';
  }
};

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'pending': return '待审核';
    case 'approved': return '已通过';
    case 'rejected': return '已拒绝';
    default: return '未知';
  }
};

// 组件挂载时加载数据
onMounted(() => {
  loadComments();
});
</script>

<style scoped>
.comment-management {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.page-description {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.header-stats {
  display: flex;
  gap: 24px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
}

.stat-value.pending {
  color: #f59e0b;
}

.filter-section {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 20px;
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.filter-group {
  display: flex;
  gap: 12px;
  flex: 1;
}

.filter-group .el-select,
.filter-group .el-input {
  min-width: 160px;
}

.action-group {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.comments-table {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

/* 评论内容样式 */
.comment-content {
  max-width: 100%;
  position: relative;
}

.comment-content p {
  margin: 0 0 0.75rem 0;
  line-height: 1.6;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: #1e293b;
  font-size: 0.875rem;
  background: rgba(59, 130, 246, 0.02);
  padding: 0.75rem;
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.1);
  transition: all 0.3s ease;
}

.comment-content p:hover {
  background: rgba(59, 130, 246, 0.05);
  border-color: rgba(59, 130, 246, 0.2);
  transform: scale(1.01);
}

.comment-meta {
  font-size: 0.75rem;
  color: #64748b;
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-top: 0.5rem;
}

.comment-meta span {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: rgba(239, 68, 68, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.1);
  transition: all 0.3s ease;
  font-weight: 500;
}

.comment-meta span:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
  transform: scale(1.05);
}


/* 现代化操作按钮样式 */
.modern-action-buttons {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.table-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 8px;
  border: 1px solid;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
  min-width: fit-content;
}

.table-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.table-btn:hover::before {
  left: 100%;
}

.table-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.table-btn:disabled:hover {
  transform: none !important;
}

/* 撤销按钮样式 */
.table-btn.revoke {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(220, 38, 38, 0.05));
  color: #dc2626;
  border-color: rgba(239, 68, 68, 0.3);
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}

.table-btn.revoke:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1));
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.25);
  transform: translateY(-2px) scale(1.02);
  color: #b91c1c;
}

.table-btn.revoke:active:not(:disabled) {
  transform: translateY(0) scale(1);
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}

/* 查看文章按钮样式 */
.table-btn.view {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.05));
  color: #2563eb;
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
}

.table-btn.view:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.1));
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.25);
  transform: translateY(-2px) scale(1.02);
  color: #1d4ed8;
}

.table-btn.view:active:not(:disabled) {
  transform: translateY(0) scale(1);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
}

/* 其他按钮样式 */
.table-btn.approve {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(22, 163, 74, 0.05));
  color: #16a34a;
  border-color: rgba(34, 197, 94, 0.3);
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.15);
}

.table-btn.approve:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.1));
  border-color: rgba(34, 197, 94, 0.4);
  box-shadow: 0 4px 15px rgba(34, 197, 94, 0.25);
  transform: translateY(-2px) scale(1.02);
  color: #15803d;
}

.table-btn.reject {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(220, 38, 38, 0.05));
  color: #dc2626;
  border-color: rgba(239, 68, 68, 0.3);
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}

.table-btn.reject:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1));
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.25);
  transform: translateY(-2px) scale(1.02);
  color: #b91c1c;
}

.table-btn.restore {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(8, 145, 178, 0.05));
  color: #0891b2;
  border-color: rgba(6, 182, 212, 0.3);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.15);
}

.table-btn.restore:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(8, 145, 178, 0.1));
  border-color: rgba(6, 182, 212, 0.4);
  box-shadow: 0 4px 15px rgba(6, 182, 212, 0.25);
  transform: translateY(-2px) scale(1.02);
  color: #0e7490;
}

/* 按钮图标样式 */
.table-btn .el-icon {
  transition: all 0.3s ease;
}

.table-btn:hover:not(:disabled) .el-icon {
  transform: scale(1.1);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .modern-page-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
  
  .title-container {
    width: 100%;
  }
  
  .modern-stats {
    width: 100%;
    justify-content: space-between;
  }
  
  .filter-row {
    flex-direction: column;
    gap: 1rem;
  }
  
  .filter-group {
    width: 100%;
    justify-content: flex-start;
  }
  
  .filter-item {
    flex: 1;
    min-width: 140px;
  }
  
  .search-item {
    min-width: 200px;
  }
  
  .action-group {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 768px) {
  .modern-page-header {
    padding: 1.5rem;
  }
  
  .title-container {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }
  
  .title-icon {
    width: 50px;
    height: 50px;
  }
  
  .page-title {
    font-size: 1.75rem;
  }
  
  .modern-stats {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .stat-card {
    width: 100%;
  }
  
  .filter-container {
    padding: 1rem;
  }
  
  .filter-group {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .filter-item {
    width: 100%;
  }
  
  .modern-select,
  .modern-input,
  .modern-search-input {
    width: 100%;
  }
  
  .action-group {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .action-btn {
    width: 100%;
    justify-content: center;
  }
  
  .modern-comments-table {
    /* 移动端表格滚动 */
  }
  
  .modern-table :deep(.el-table__body-wrapper) {
    overflow-x: auto;
  }
  
  .modern-table :deep(.el-table__row:hover) {
    transform: none;
  }
  
  .modern-action-buttons {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .table-btn {
    width: 100%;
    justify-content: center;
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
  }
}

@media (max-width: 640px) {
  .modern-stats {
    gap: 0.5rem;
  }
  
  .stat-card {
    padding: 0.75rem;
  }
  
  .stat-icon {
    width: 35px;
    height: 35px;
  }
  
  .stat-value {
    font-size: 1.125rem;
  }
  
  .action-btn span {
    display: none;
  }
  
  .table-btn span {
    font-size: 0.7rem;
  }
  
  .comment-content p {
    padding: 0.5rem;
    font-size: 0.8rem;
  }
  
  .comment-meta {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
}

/* 现代化状态徽章 */
.modern-status-badge {
  display: flex;
  justify-content: center;
  align-items: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  border: 1px solid;
}

.modern-status-badge.pending .status-indicator {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.1));
  color: #d97706;
  border-color: rgba(245, 158, 11, 0.3);
}

.modern-status-badge.approved .status-indicator {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(22, 163, 74, 0.1));
  color: #16a34a;
  border-color: rgba(34, 197, 94, 0.3);
}

.modern-status-badge.rejected .status-indicator {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1));
  color: #dc2626;
  border-color: rgba(239, 68, 68, 0.3);
}

.status-indicator:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

/* 时间显示样式 */
.time-display {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  background: rgba(6, 182, 212, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(6, 182, 212, 0.1);
  font-size: 0.875rem;
  color: #0891b2;
  font-weight: 500;
  transition: all 0.3s ease;
}

.time-display:hover {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.2);
  transform: scale(1.02);
}

/* 用户ID显示样式 */
.user-id-display {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  background: rgba(139, 92, 246, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(139, 92, 246, 0.1);
  font-size: 0.875rem;
  color: #8b5cf6;
  font-weight: 500;
  transition: all 0.3s ease;
  justify-content: center;
}

.user-id-display:hover {
  background: rgba(139, 92, 246, 0.1);
  border-color: rgba(139, 92, 246, 0.2);
  transform: scale(1.02);
}

.action-btn .is-loading {
  animation: rotate 1s linear infinite;
}

.table-btn .is-loading {
  animation: rotate 1s linear infinite;
}
</style>