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
          <el-button @click="loadComments" :loading="loading" icon="Refresh">刷新</el-button>
          <el-button 
            type="danger" 
            :disabled="selectedComments.length === 0"
            @click="handleBatchAction('reject')"
            icon="Delete"
          >
            批量拒绝 ({{ selectedComments.length }})
          </el-button>
          <el-button 
            type="success" 
            :disabled="selectedComments.length === 0"
            @click="handleBatchAction('approve')"
            icon="Check"
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
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.status)"
              size="small"
            >
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="content" label="评论内容" min-width="300">
          <template #default="{ row }">
            <div class="comment-content">
              <p>{{ row.content }}</p>
              <div class="comment-meta">
                <span>文章ID: {{ row.article_id }}</span>
                <span v-if="row.parent_id">• 回复ID: {{ row.parent_id }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="user_id" label="用户ID" width="100" />
        
        <el-table-column prop="created_at" label="发表时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                v-if="row.status === 'pending'"
                type="success"
                size="small"
                @click="handleModerate(row, 'approve')"
                :loading="moderatingIds.has(row.id)"
              >
                通过
              </el-button>
              
              <el-button
                v-if="row.status === 'pending'"
                type="danger"
                size="small"
                @click="handleModerate(row, 'reject')"
                :loading="moderatingIds.has(row.id)"
              >
                拒绝
              </el-button>
              
              <el-button
                v-if="row.status === 'approved'"
                type="warning"
                size="small"
                @click="handleModerate(row, 'reject')"
                :loading="moderatingIds.has(row.id)"
              >
                撤销
              </el-button>
              
              <el-button
                v-if="row.status === 'rejected'"
                type="success"
                size="small"
                @click="handleModerate(row, 'approve')"
                :loading="moderatingIds.has(row.id)"
              >
                恢复
              </el-button>
              
              <el-button
                size="small"
                @click="viewArticle(row.article_id)"
                icon="View"
              >
                查看文章
              </el-button>
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

.comment-content {
  max-width: 100%;
}

.comment-content p {
  margin: 0 0 8px 0;
  line-height: 1.5;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.comment-meta {
  font-size: 12px;
  color: #6b7280;
  display: flex;
  gap: 8px;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  min-width: auto;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  margin-top: 20px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-stats {
    align-self: stretch;
    justify-content: space-around;
  }
  
  .filter-row {
    flex-direction: column;
    gap: 12px;
  }
  
  .filter-group {
    flex-direction: column;
  }
  
  .filter-group .el-select,
  .filter-group .el-input {
    min-width: auto;
  }
  
  .action-group {
    justify-content: stretch;
  }
  
  .action-group .el-button {
    flex: 1;
    text-align: center;
  }
  
  .comments-table {
    /* 移动端隐藏部分列 */
  }
  
  .comments-table :deep(.el-table__body-wrapper) {
    overflow-x: auto;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 2px;
  }
  
  .action-buttons .el-button {
    font-size: 12px;
    padding: 4px 8px;
  }
}

@media (max-width: 480px) {
  .comment-management {
    padding: 0 8px;
  }
  
  .page-title {
    font-size: 24px;
  }
  
  .header-stats {
    gap: 16px;
  }
  
  .stat-item {
    flex: 1;
  }
  
  .filter-section,
  .comments-table,
  .pagination-wrapper,
  .empty-state {
    border-radius: 6px;
    border: none;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
}
</style>