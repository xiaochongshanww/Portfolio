<template>
  <div class="category-management">
    <!-- 现代化页面头部 -->
    <div class="modern-page-header">
      <div class="page-header">
        <div class="title-container">
          <div class="title-icon">
            <el-icon size="28"><DataBoard /></el-icon>
          </div>
          <div class="header-content">
            <h1 class="page-title">分类管理</h1>
            <p class="page-description">管理文章分类，构建清晰的内容结构</p>
          </div>
        </div>
        <div class="header-actions">
          <button @click="loadData" :disabled="loading" class="action-btn secondary">
            <el-icon size="16" :class="{ 'is-loading': loading }"><Refresh /></el-icon>
            <span>刷新</span>
          </button>
          <button @click="showCreateDialog" class="action-btn primary">
            <el-icon size="16"><Plus /></el-icon>
            <span>新建分类</span>
          </button>
        </div>
      </div>
      
      <!-- 统计面板 -->
      <div class="modern-stats">
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><DataBoard /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">总分类</span>
              <span class="stat-value">{{ stats.total_categories }}</span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><Folder /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">已使用</span>
              <span class="stat-value active">{{ stats.categories_with_articles }}</span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><Folder /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">未使用</span>
              <span class="stat-value unused">{{ stats.unused_categories }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 现代化分类表格 -->
    <div class="modern-categories-table">
      <el-table
        v-loading="loading"
        :data="treeData"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        default-expand-all
        size="default"
        class="modern-table"
      >
        <el-table-column prop="name" label="分类名称" min-width="200">
          <template #default="{ row }">
            <div class="category-name">
              <el-icon class="category-icon"><Folder /></el-icon>
              <span>{{ row.name }}</span>
              <el-tag v-if="row.article_count > 0" size="small" class="count-tag">
                {{ row.article_count }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="slug" label="Slug" width="200">
          <template #default="{ row }">
            <code class="slug-code">{{ row.slug }}</code>
          </template>
        </el-table-column>
        
        <el-table-column prop="article_count" label="文章数量" width="120" align="center">
          <template #default="{ row }">
            <div class="article-count-container">
              <el-tag 
                :type="row.article_count > 0 ? 'success' : 'info'"
                size="small"
                class="article-count-tag"
              >
                {{ row.article_count }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                size="small"
                @click="showEditDialog(row)"
                :icon="Edit"
                class="action-btn-edit"
              >
                编辑
              </el-button>
              
              <el-button
                size="small"
                type="primary"
                @click="showCreateDialog(row)"
                :icon="Plus"
                class="action-btn-add"
              >
                添加子类
              </el-button>
              
              <el-button
                size="small"
                type="danger"
                @click="handleDelete(row)"
                :icon="Delete"
                class="action-btn-delete"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && categories.length === 0" class="empty-state">
      <el-empty description="暂无分类数据">
        <el-button type="primary" @click="showCreateDialog">创建第一个分类</el-button>
      </el-empty>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建分类' : '编辑分类'"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="80px"
      >
        <el-form-item label="分类名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入分类名称"
            @input="generateSlug"
          />
        </el-form-item>
        
        <el-form-item label="Slug" prop="slug">
          <el-input
            v-model="form.slug"
            placeholder="URL友好的标识符，留空自动生成"
          />
        </el-form-item>
        
        <el-form-item label="父分类" prop="parent_id">
          <el-select
            v-model="form.parent_id"
            placeholder="选择父分类（可选）"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="category in parentOptions"
              :key="category.id"
              :label="category.name"
              :value="category.id"
              :disabled="category.id === editingId"
            />
          </el-select>
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
import { Plus, Folder, Edit, Delete, Refresh, DataBoard } from '@element-plus/icons-vue';
import api from '../../apiClient';

// 响应式数据
const loading = ref(false);
const submitting = ref(false);
const dialogVisible = ref(false);
const dialogMode = ref('create');
const editingId = ref(null);

const categories = ref([]);
const formRef = ref();

// 统计数据
const stats = reactive({
  total_categories: 0,
  categories_with_articles: 0,
  unused_categories: 0
});

// 表单数据
const form = reactive({
  name: '',
  slug: '',
  parent_id: null
});

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  slug: [
    { pattern: /^[a-z0-9-]*$/, message: 'Slug只能包含小写字母、数字和连字符', trigger: 'blur' }
  ]
};

// 计算属性：构建树形数据
const treeData = computed(() => {
  const buildTree = (items, parentId = null) => {
    return items
      .filter(item => item.parent_id === parentId)
      .map(item => ({
        ...item,
        children: buildTree(items, item.id)
      }));
  };
  return buildTree(categories.value);
});

// 计算属性：父分类选项（用于下拉选择）
const parentOptions = computed(() => {
  const getOptions = (items, level = 0) => {
    let options = [];
    items.forEach(item => {
      options.push({
        id: item.id,
        name: '　'.repeat(level) + item.name
      });
      if (item.children && item.children.length > 0) {
        options.push(...getOptions(item.children, level + 1));
      }
    });
    return options;
  };
  return getOptions(treeData.value);
});

// 加载数据
const loadData = async () => {
  if (loading.value) return;
  
  try {
    loading.value = true;
    const response = await api.get('/taxonomy/stats');
    
    if (response.data.code === 0) {
      const data = response.data.data;
      categories.value = data.categories;
      Object.assign(stats, data.summary);
    } else {
      ElMessage.error(response.data.message || '加载数据失败');
    }
  } catch (error) {
    console.error('加载分类数据失败:', error);
    ElMessage.error('加载分类数据失败');
  } finally {
    loading.value = false;
  }
};

// 显示创建对话框
const showCreateDialog = (parent = null) => {
  dialogMode.value = 'create';
  editingId.value = null;
  resetForm();
  if (parent) {
    form.parent_id = parent.id;
  }
  dialogVisible.value = true;
};

// 显示编辑对话框
const showEditDialog = (category) => {
  dialogMode.value = 'edit';
  editingId.value = category.id;
  form.name = category.name;
  form.slug = category.slug;
  form.parent_id = category.parent_id;
  dialogVisible.value = true;
};

// 重置表单
const resetForm = () => {
  form.name = '';
  form.slug = '';
  form.parent_id = null;
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
      slug: form.slug.trim() || undefined,
      parent_id: form.parent_id || undefined
    };
    
    let response;
    if (dialogMode.value === 'create') {
      response = await api.post('/taxonomy/categories/', data);
    } else {
      response = await api.patch(`/taxonomy/categories/${editingId.value}`, data);
    }
    
    if (response.data.code === 0) {
      ElMessage.success(
        dialogMode.value === 'create' ? '分类创建成功' : '分类更新成功'
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

// 删除分类
const handleDelete = async (category) => {
  try {
    let confirmMessage = '';
    let confirmTitle = '';
    let confirmOptions = {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    };
    
    if (category.article_count > 0) {
      // 有文章的分类 - 警告式删除
      confirmMessage = `⚠️ 警告：分类「${category.name}」下还有 ${category.article_count} 篇文章！
      
删除此分类后，这些文章将变为「未分类」状态。

确定要继续删除吗？此操作不可恢复！`;
      confirmTitle = '危险操作确认';
      confirmOptions = {
        type: 'error',
        confirmButtonText: '我已了解风险，继续删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
        dangerouslyUseHTMLString: false
      };
    } else {
      // 空分类 - 普通删除确认
      confirmMessage = `确定要删除分类「${category.name}」吗？此操作不可恢复！`;
      confirmTitle = '删除确认';
      confirmOptions = {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      };
    }
    
    await ElMessageBox.confirm(confirmMessage, confirmTitle, confirmOptions);
    
    const response = await api.delete(`/taxonomy/categories/${category.id}`);
    
    if (response.data.code === 0) {
      // 根据是否有文章提供不同的成功信息
      if (category.article_count > 0) {
        ElMessage.success(`分类「${category.name}」删除成功，${category.article_count} 篇文章已转为未分类状态`);
      } else {
        ElMessage.success(`分类「${category.name}」删除成功`);
      }
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

// 组件挂载时加载数据
onMounted(() => {
  loadData();
});
</script>

<style scoped>
/* ===== 现代化分类管理页面样式 ===== */
.category-management {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: 
    radial-gradient(circle at 20% 80%, rgba(34, 197, 94, 0.05) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(16, 185, 129, 0.05) 0%, transparent 50%),
    radial-gradient(circle at 40% 40%, rgba(6, 182, 212, 0.05) 0%, transparent 50%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
}

/* 现代化页面头部 */
.modern-page-header {
  position: relative;
  background: 
    linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(16, 185, 129, 0.05)),
    rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 2.5rem;
  margin-bottom: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.modern-page-header::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(16, 185, 129, 0.05));
  border-radius: 50%;
  filter: blur(40px);
  animation: float-decoration 8s ease-in-out infinite;
}

@keyframes float-decoration {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-30px) rotate(180deg); }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  position: relative;
  z-index: 2;
  margin-bottom: 1.5rem;
}

.title-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-icon {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #10b981 0%, #22c55e 100%);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 30px rgba(34, 197, 94, 0.3);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.title-icon::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.3) 50%, transparent 60%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.title-icon:hover::before {
  transform: rotate(45deg) translateX(100%);
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 0.5rem 0;
  font-size: 2.25rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #10b981 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.page-description {
  margin: 0;
  color: #64748b;
  font-size: 1.125rem;
  font-weight: 400;
  line-height: 1.6;
}

/* 统计面板 */
.modern-stats {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  flex: 1;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #10b981, #22c55e);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  border-color: rgba(34, 197, 94, 0.2);
}

.stat-card:hover::before {
  height: 4px;
  background: linear-gradient(90deg, #22c55e, #16a34a);
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.stat-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(16, 185, 129, 0.05));
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #10b981;
  transition: all 0.3s ease;
}

.stat-card:hover .stat-icon {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.1));
  transform: scale(1.1) rotate(5deg);
}

.stat-info {
  flex: 1;
}

.stat-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  display: block;
  font-size: 2rem;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
  transition: all 0.3s ease;
}

.stat-value.active {
  color: #10b981;
}

.stat-value.unused {
  color: #f59e0b;
}

.stat-card:hover .stat-value {
  transform: scale(1.05);
}

/* 操作按钮组 */
.header-actions {
  display: flex;
  gap: 0.75rem;
  flex-shrink: 0;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 12px;
  border: none;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.action-btn.primary {
  background: linear-gradient(135deg, #10b981, #22c55e);
  color: white;
  box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
}

.action-btn.primary:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(34, 197, 94, 0.4);
  background: linear-gradient(135deg, #22c55e, #16a34a);
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.8);
  color: #64748b;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.action-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.95);
  color: #1e293b;
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  border-color: rgba(34, 197, 94, 0.2);
}

.action-btn .is-loading {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 分类表格 */
.modern-categories-table {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  overflow: hidden;
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
  margin-bottom: 2rem;
}

.modern-table :deep(.el-table__header-wrapper) {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.05), rgba(16, 185, 129, 0.02));
  border-radius: 20px 20px 0 0;
}

.modern-table :deep(.el-table__header) {
  background: transparent;
}

.modern-table :deep(.el-table__body tr) {
  transition: all 0.3s ease;
  border: none;
}

.modern-table :deep(.el-table__body tr:hover) {
  background: rgba(34, 197, 94, 0.02);
  transform: scale(1.005);
}

.modern-table :deep(.el-table::before) {
  display: none;
}

.modern-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

/* 分类名称样式 */
.category-name {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 600;
  color: #1e293b;
}

.category-icon {
  color: #10b981;
  transition: all 0.3s ease;
}

.category-name:hover .category-icon {
  transform: scale(1.2) rotate(10deg);
  color: #22c55e;
}

.count-tag {
  background: linear-gradient(135deg, #10b981, #22c55e);
  color: white;
  border: none;
  font-weight: 600;
}

/* Slug 代码样式 */
.slug-code {
  background: rgba(34, 197, 94, 0.05);
  color: #10b981;
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid rgba(34, 197, 94, 0.1);
  transition: all 0.3s ease;
}

.slug-code:hover {
  background: rgba(34, 197, 94, 0.1);
  transform: scale(1.05);
  border-color: rgba(34, 197, 94, 0.2);
}

/* 文章数量样式 */
.article-count-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.article-count-tag {
  font-weight: 600;
  min-width: 32px;
  text-align: center;
  border-radius: 16px;
  transition: all 0.3s ease;
}

.article-count-tag:hover {
  transform: scale(1.1);
}

/* 表格列分隔线 */
.modern-table :deep(.el-table__header th) {
  background: transparent !important;
  border: none;
  border-right: 1px solid rgba(229, 231, 235, 0.6);
  color: #1e293b;
  font-weight: 700;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 1.5rem 1rem;
}

.modern-table :deep(.el-table__header th:last-child) {
  border-right: none;
}

.modern-table :deep(.el-table__body td) {
  border: none;
  border-right: 1px solid rgba(229, 231, 235, 0.4);
  padding: 1.25rem 1rem;
  vertical-align: middle;
}

.modern-table :deep(.el-table__body td:last-child) {
  border-right: none;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: nowrap;
  justify-content: flex-start;
}

.action-buttons .el-button {
  min-width: auto;
  border-radius: 6px;
  font-weight: 500;
  font-size: 12px;
  padding: 4px 8px;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.action-buttons .el-button:hover {
  transform: translateY(-1px) scale(1.05);
}

.action-btn-edit {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
}

.action-btn-edit:hover {
  background: #3b82f6;
  color: white;
}

.action-btn-add {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
  color: #22c55e;
}

.action-btn-add:hover {
  background: #22c55e;
  color: white;
}

.action-btn-delete {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.action-btn-delete:hover {
  background: #ef4444;
  color: white;
}

/* 空状态样式 */
.empty-state {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 3rem;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
}

/* 对话框样式 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1rem;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .modern-page-header {
    flex-direction: column;
    gap: 1.5rem;
    align-items: flex-start;
  }
  
  .title-container {
    width: 100%;
  }
  
  .modern-stats {
    width: 100%;
    justify-content: space-between;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 768px) {
  .category-management {
    padding: 1rem;
  }
  
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
    font-size: 1.875rem;
  }
  
  .modern-stats {
    flex-direction: column;
    gap: 1rem;
  }
  
  .stat-card {
    width: 100%;
  }
  
  .header-actions {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .action-btn {
    width: 100%;
    justify-content: center;
  }
  
  .modern-categories-table {
    border-radius: 16px;
  }
  
  .modern-table :deep(.el-table__body-wrapper) {
    overflow-x: auto;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 0.25rem;
    width: 100%;
  }
  
  .action-buttons .el-button {
    width: 100%;
    font-size: 0.75rem;
    padding: 0.5rem;
    justify-content: center;
  }
}

@media (max-width: 640px) {
  .modern-stats {
    gap: 0.75rem;
  }
  
  .stat-card {
    padding: 1rem;
  }
  
  .stat-icon {
    width: 40px;
    height: 40px;
  }
  
  .stat-value {
    font-size: 1.5rem;
  }
  
  .modern-categories-table {
    border-radius: 12px;
  }
}
</style>