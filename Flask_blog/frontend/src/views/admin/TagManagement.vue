<template>
  <div class="tag-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">标签管理</h1>
        <p class="page-description">管理文章标签，提升内容可发现性</p>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-label">总标签</span>
          <span class="stat-value">{{ stats.total_tags }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已使用</span>
          <span class="stat-value active">{{ stats.tags_with_articles }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">未使用</span>
          <span class="stat-value unused">{{ stats.unused_tags }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="loadData" :loading="loading" icon="Refresh">刷新</el-button>
        <el-button 
          type="danger" 
          @click="cleanUnusedTags"
          :disabled="stats.unused_tags === 0"
          icon="Delete"
        >
          清理未使用 ({{ stats.unused_tags }})
        </el-button>
        <el-button type="primary" @click="showCreateDialog" icon="Plus">
          新建标签
        </el-button>
      </div>
    </div>

    <!-- 筛选和搜索 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-group">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索标签名称..."
            clearable
            @input="handleSearch"
            style="width: 300px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-select v-model="sortBy" placeholder="排序方式" @change="handleSort">
            <el-option label="按使用量降序" value="usage_desc" />
            <el-option label="按使用量升序" value="usage_asc" />
            <el-option label="按名称A-Z" value="name_asc" />
            <el-option label="按名称Z-A" value="name_desc" />
            <el-option label="按创建时间" value="created_desc" />
          </el-select>
        </div>
        
        <div class="view-toggle">
          <el-radio-group v-model="viewMode" @change="handleViewModeChange">
            <el-radio-button label="table">表格视图</el-radio-button>
            <el-radio-button label="cloud">标签云</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </div>

    <!-- 表格视图 -->
    <div v-if="viewMode === 'table'" class="tags-table">
      <el-table
        v-loading="loading"
        :data="filteredTags"
        @selection-change="handleSelectionChange"
        size="default"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="name" label="标签名称" min-width="200">
          <template #default="{ row }">
            <div class="tag-name">
              <el-tag :type="getTagType(row.article_count)" size="default">
                {{ row.name }}
              </el-tag>
              <span class="article-count">({{ row.article_count }})</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="slug" label="Slug" width="200">
          <template #default="{ row }">
            <code class="slug-code">{{ row.slug }}</code>
          </template>
        </el-table-column>
        
        <el-table-column prop="article_count" label="使用次数" width="120" align="center" sortable>
          <template #default="{ row }">
            <el-progress 
              :percentage="getUsagePercentage(row.article_count)"
              :stroke-width="6"
              :show-text="false"
              :color="getProgressColor(row.article_count)"
              style="width: 60px; margin-right: 8px;"
            />
            <span>{{ row.article_count }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                size="small"
                @click="showEditDialog(row)"
                icon="Edit"
              >
                编辑
              </el-button>
              
              <el-button
                size="small"
                type="danger"
                @click="handleDelete(row)"
                :disabled="row.article_count > 0"
                icon="Delete"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 标签云视图 -->
    <div v-else class="tag-cloud">
      <div class="cloud-container">
        <div 
          v-for="tag in filteredTags" 
          :key="tag.id"
          class="cloud-tag"
          :class="{ 'unused': tag.article_count === 0 }"
          :style="getCloudTagStyle(tag)"
          @click="showEditDialog(tag)"
        >
          <span class="tag-text">{{ tag.name }}</span>
          <span class="tag-count">({{ tag.article_count }})</span>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && tags.length === 0" class="empty-state">
      <el-empty description="暂无标签数据">
        <el-button type="primary" @click="showCreateDialog">创建第一个标签</el-button>
      </el-empty>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建标签' : '编辑标签'"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="80px"
      >
        <el-form-item label="标签名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入标签名称"
            @input="generateSlug"
          />
        </el-form-item>
        
        <el-form-item label="Slug" prop="slug">
          <el-input
            v-model="form.slug"
            placeholder="URL友好的标识符，留空自动生成"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            @click="handleSubmit"
            :loading="submitting"
          >
            {{ dialogMode === 'create' ? '创建' : '保存' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search, Edit, Delete, Refresh } from '@element-plus/icons-vue';
import api from '../../apiClient';

// 响应式数据
const loading = ref(false);
const submitting = ref(false);
const dialogVisible = ref(false);
const dialogMode = ref('create');
const editingId = ref(null);
const searchKeyword = ref('');
const sortBy = ref('usage_desc');
const viewMode = ref('table');
const selectedTags = ref([]);

const tags = ref([]);
const formRef = ref();

// 统计数据
const stats = reactive({
  total_tags: 0,
  tags_with_articles: 0,
  unused_tags: 0
});

// 表单数据
const form = reactive({
  name: '',
  slug: ''
});

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入标签名称', trigger: 'blur' },
    { min: 1, max: 80, message: '长度在 1 到 80 个字符', trigger: 'blur' }
  ],
  slug: [
    { pattern: /^[a-z0-9-]*$/, message: 'Slug只能包含小写字母、数字和连字符', trigger: 'blur' }
  ]
};

// 计算属性：筛选后的标签
const filteredTags = computed(() => {
  let filtered = [...tags.value];
  
  // 搜索筛选
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase();
    filtered = filtered.filter(tag => 
      tag.name.toLowerCase().includes(keyword) ||
      tag.slug.toLowerCase().includes(keyword)
    );
  }
  
  // 排序
  filtered.sort((a, b) => {
    switch (sortBy.value) {
      case 'usage_desc':
        return b.article_count - a.article_count;
      case 'usage_asc':
        return a.article_count - b.article_count;
      case 'name_asc':
        return a.name.localeCompare(b.name);
      case 'name_desc':
        return b.name.localeCompare(a.name);
      case 'created_desc':
      default:
        return b.id - a.id;
    }
  });
  
  return filtered;
});

// 加载数据
const loadData = async () => {
  if (loading.value) return;
  
  try {
    loading.value = true;
    const response = await api.get('/taxonomy/stats');
    
    if (response.data.code === 0) {
      const data = response.data.data;
      tags.value = data.tags;
      Object.assign(stats, data.summary);
    } else {
      ElMessage.error(response.data.message || '加载数据失败');
    }
  } catch (error) {
    console.error('加载标签数据失败:', error);
    ElMessage.error('加载标签数据失败');
  } finally {
    loading.value = false;
  }
};

// 显示创建对话框
const showCreateDialog = () => {
  dialogMode.value = 'create';
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
};

// 显示编辑对话框
const showEditDialog = (tag) => {
  dialogMode.value = 'edit';
  editingId.value = tag.id;
  form.name = tag.name;
  form.slug = tag.slug;
  dialogVisible.value = true;
};

// 重置表单
const resetForm = () => {
  form.name = '';
  form.slug = '';
  if (formRef.value) {
    formRef.value.resetFields();
  }
};

// 根据名称生成Slug
const generateSlug = () => {
  if (!form.slug && form.name) {
    form.slug = form.name
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fa5]/g, '-')
      .replace(/--+/g, '-')
      .replace(/^-|-$/g, '');
  }
};

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return;
  
  try {
    await formRef.value.validate();
    
    submitting.value = true;
    
    const data = {
      name: form.name.trim(),
      slug: form.slug.trim() || undefined
    };
    
    let response;
    if (dialogMode.value === 'create') {
      response = await api.post('/taxonomy/tags/', data);
    } else {
      response = await api.patch(`/taxonomy/tags/${editingId.value}`, data);
    }
    
    if (response.data.code === 0) {
      ElMessage.success(
        dialogMode.value === 'create' ? '标签创建成功' : '标签更新成功'
      );
      dialogVisible.value = false;
      await loadData();
    } else {
      ElMessage.error(response.data.message || '操作失败');
    }
  } catch (error) {
    if (error !== 'validation failed') {
      console.error('提交失败:', error);
      ElMessage.error('操作失败');
    }
  } finally {
    submitting.value = false;
  }
};

// 删除标签
const handleDelete = async (tag) => {
  if (tag.article_count > 0) {
    ElMessage.warning('该标签还在使用中，无法删除');
    return;
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除标签「${tag.name}」吗？此操作不可恢复！`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    );
    
    const response = await api.delete(`/taxonomy/tags/${tag.id}`);
    
    if (response.data.code === 0) {
      ElMessage.success('标签删除成功');
      await loadData();
    } else {
      ElMessage.error(response.data.message || '删除失败');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error);
      ElMessage.error('删除失败');
    }
  }
};

// 清理未使用的标签
const cleanUnusedTags = async () => {
  const unusedTags = tags.value.filter(tag => tag.article_count === 0);
  
  if (unusedTags.length === 0) {
    ElMessage.info('没有未使用的标签');
    return;
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${unusedTags.length} 个未使用的标签吗？此操作不可恢复！`,
      '清理确认',
      {
        type: 'warning',
        confirmButtonText: '确定清理',
        cancelButtonText: '取消'
      }
    );
    
    for (const tag of unusedTags) {
      await api.delete(`/taxonomy/tags/${tag.id}`);
    }
    
    ElMessage.success(`成功清理 ${unusedTags.length} 个未使用的标签`);
    await loadData();
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清理失败:', error);
      ElMessage.error('清理失败');
    }
  }
};

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedTags.value = selection;
};

// 处理搜索
const handleSearch = () => {
  // 搜索是响应式的，不需要额外处理
};

// 处理排序
const handleSort = () => {
  // 排序是响应式的，不需要额外处理
};

// 处理视图模式变化
const handleViewModeChange = () => {
  // 视图模式是响应式的，不需要额外处理
};

// 获取标签类型
const getTagType = (count) => {
  if (count === 0) return 'info';
  if (count >= 10) return 'danger';
  if (count >= 5) return 'warning';
  return 'success';
};

// 获取使用百分比
const getUsagePercentage = (count) => {
  const maxCount = Math.max(...tags.value.map(t => t.article_count));
  return maxCount === 0 ? 0 : Math.round((count / maxCount) * 100);
};

// 获取进度条颜色
const getProgressColor = (count) => {
  if (count === 0) return '#e5e7eb';
  if (count >= 10) return '#ef4444';
  if (count >= 5) return '#f59e0b';
  return '#10b981';
};

// 获取标签云样式
const getCloudTagStyle = (tag) => {
  const baseSize = 14;
  const maxSize = 32;
  const maxCount = Math.max(...tags.value.map(t => t.article_count));
  const size = maxCount === 0 ? baseSize : 
    baseSize + (tag.article_count / maxCount) * (maxSize - baseSize);
  
  return {
    fontSize: size + 'px',
    opacity: tag.article_count === 0 ? 0.5 : 1
  };
};

// 组件挂载时加载数据
onMounted(() => {
  loadData();
});
</script>

<style scoped>
.tag-management {
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
  margin: 0 24px;
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

.stat-value.active {
  color: #10b981;
}

.stat-value.unused {
  color: #f59e0b;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
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

.view-toggle {
  flex-shrink: 0;
}

.tags-table {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.tag-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.article-count {
  color: #6b7280;
  font-size: 12px;
}

.slug-code {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #374151;
}

.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.action-buttons .el-button {
  min-width: auto;
}

/* 标签云样式 */
.tag-cloud {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 30px;
  min-height: 400px;
}

.cloud-container {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
  align-items: center;
}

.cloud-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.cloud-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.cloud-tag.unused {
  background: #e5e7eb;
  color: #6b7280;
}

.tag-text {
  line-height: 1;
}

.tag-count {
  font-size: 0.8em;
  opacity: 0.8;
}

.empty-state {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
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
    margin: 0;
  }
  
  .header-actions {
    align-self: stretch;
    justify-content: stretch;
  }
  
  .header-actions .el-button {
    flex: 1;
    font-size: 12px;
  }
  
  .filter-row {
    flex-direction: column;
    gap: 12px;
  }
  
  .filter-group {
    flex-direction: column;
  }
  
  .view-toggle {
    align-self: stretch;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 2px;
  }
  
  .action-buttons .el-button {
    font-size: 12px;
    padding: 4px 8px;
  }
  
  .cloud-container {
    gap: 8px;
  }
  
  .cloud-tag {
    padding: 6px 12px;
    font-size: 14px !important;
  }
}

@media (max-width: 480px) {
  .tag-management {
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
  .tags-table,
  .tag-cloud,
  .empty-state {
    border-radius: 6px;
    border: none;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
}
</style>

<style scoped>
.tag-management {
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

.header-actions {
  display: flex;
  gap: 12px;
}

.development-notice {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 24px;
}

.feature-preview {
  margin-top: 20px;
}

.feature-preview h3 {
  margin: 0 0 16px 0;
  color: #1f2937;
  font-size: 18px;
}

.feature-preview ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-preview li {
  padding: 8px 0;
  color: #4b5563;
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
}
</style>