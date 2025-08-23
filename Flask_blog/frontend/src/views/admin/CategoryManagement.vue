<template>
  <div class="category-management">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">分类管理</h1>
        <p class="page-description">管理文章分类，构建清晰的内容结构</p>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-label">总分类</span>
          <span class="stat-value">{{ stats.total_categories }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已使用</span>
          <span class="stat-value active">{{ stats.categories_with_articles }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">未使用</span>
          <span class="stat-value unused">{{ stats.unused_categories }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="loadData" :loading="loading" icon="Refresh">刷新</el-button>
        <el-button type="primary" @click="showCreateDialog" icon="Plus">
          新建分类
        </el-button>
      </div>
    </div>

    <!-- 分类表格 -->
    <div class="categories-table">
      <el-table
        v-loading="loading"
        :data="treeData"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        default-expand-all
        size="default"
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
            <el-badge 
              :value="row.article_count" 
              :type="row.article_count > 0 ? 'primary' : 'info'"
              :hidden="row.article_count === 0"
            >
              <span class="article-count">{{ row.article_count }}</span>
            </el-badge>
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
                @click="showCreateDialog(row)"
                icon="Plus"
              >
                添加子分类
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
import { Plus, Folder, Edit, Delete } from '@element-plus/icons-vue';
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
  if (category.article_count > 0) {
    ElMessage.warning('该分类下还有文章，无法删除');
    return;
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除分类「${category.name}」吗？此操作不可恢复！`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    );
    
    const response = await api.delete(`/taxonomy/categories/${category.id}`);
    
    if (response.data.code === 0) {
      ElMessage.success('分类删除成功');
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
.category-management {
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