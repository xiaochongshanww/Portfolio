<template>
  <div class="taxonomy-admin-page">
    <h1>分类与标签管理</h1>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="分类管理" name="categories">
        <div class="toolbar">
          <el-button type="primary" @click="handleOpenCategoryDialog()">新建分类</el-button>
        </div>
        <el-table :data="categories" v-loading="loading.categories" border stripe>
          <el-table-column prop="id" label="ID" width="80"></el-table-column>
          <el-table-column prop="name" label="名称"></el-table-column>
          <el-table-column prop="slug" label="Slug"></el-table-column>
          <el-table-column prop="parent_id" label="父分类ID" width="100"></el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="scope">
              <el-button size="small" @click="handleOpenCategoryDialog(scope.row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete('category', scope.row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="标签管理" name="tags">
        <div class="toolbar">
          <el-button type="primary" @click="handleOpenTagDialog()">新建标签</el-button>
        </div>
        <el-table :data="tags" v-loading="loading.tags" border stripe>
          <el-table-column prop="id" label="ID" width="80"></el-table-column>
          <el-table-column prop="name" label="名称"></el-table-column>
          <el-table-column prop="slug" label="Slug"></el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="scope">
              <el-button size="small" @click="handleOpenTagDialog(scope.row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete('tag', scope.row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 分类编辑/新建弹窗 -->
    <el-dialog v-model="dialogVisible.category" :title="isEditMode.category ? '编辑分类' : '新建分类'" width="500px">
      <el-form :model="forms.category" ref="categoryForm" label-width="80px">
        <el-form-item label="名称" prop="name" required>
          <el-input v-model="forms.category.name"></el-input>
        </el-form-item>
        <el-form-item label="Slug" prop="slug">
          <el-input v-model="forms.category.slug" placeholder="留空则自动生成"></el-input>
        </el-form-item>
        <el-form-item label="父分类" prop="parent_id">
          <el-select v-model="forms.category.parent_id" placeholder="选择父分类" clearable>
            <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible.category = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCategory" :loading="saving.category">保存</el-button>
      </template>
    </el-dialog>

    <!-- 标签编辑/新建弹窗 -->
    <el-dialog v-model="dialogVisible.tag" :title="isEditMode.tag ? '编辑标签' : '新建标签'" width="500px">
      <el-form :model="forms.tag" ref="tagForm" label-width="80px">
        <el-form-item label="名称" prop="name" required>
          <el-input v-model="forms.tag.name"></el-input>
        </el-form-item>
        <el-form-item label="Slug" prop="slug">
          <el-input v-model="forms.tag.slug" placeholder="留空则自动生成"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible.tag = false">取消</el-button>
        <el-button type="primary" @click="handleSaveTag" :loading="saving.tag">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import apiClient from '../apiClient'; // 假设 apiClient 已配置好

const activeTab = ref('categories');
const categories = ref([]);
const tags = ref([]);

const loading = reactive({
  categories: false,
  tags: false,
});

const saving = reactive({
  category: false,
  tag: false,
});

const dialogVisible = reactive({
  category: false,
  tag: false,
});

const isEditMode = reactive({
  category: false,
  tag: false,
});

const forms = reactive({
  category: { id: null, name: '', slug: '', parent_id: null },
  tag: { id: null, name: '', slug: '' },
});

// --- API 调用封装 ---
// 注意：这里的 API 调用路径是根据后端 taxonomy/routes.py 推断的。
// 实际项目中，这些应该通过生成的 OpenAPI 客户端来调用。
const api = {
  getCategories: () => apiClient.get('/taxonomy/categories/'),
  createCategory: (data) => apiClient.post('/taxonomy/categories/', data),
  updateCategory: (id, data) => apiClient.patch(`/taxonomy/categories/${id}`, data),
  deleteCategory: (id) => apiClient.delete(`/taxonomy/categories/${id}`),
  getTags: () => apiClient.get('/taxonomy/tags/'),
  createTag: (data) => apiClient.post('/taxonomy/tags/', data),
  updateTag: (id, data) => apiClient.patch(`/taxonomy/tags/${id}`, data),
  deleteTag: (id) => apiClient.delete(`/taxonomy/tags/${id}`),
};

// --- 数据获取 ---
const fetchCategories = async () => {
  loading.categories = true;
  try {
    const response = await api.getCategories();
    categories.value = response.data.data;
  } catch (error) {
    ElMessage.error('获取分类列表失败');
    console.error(error);
  } finally {
    loading.categories = false;
  }
};

const fetchTags = async () => {
  loading.tags = true;
  try {
    const response = await api.getTags();
    tags.value = response.data.data;
  } catch (error) {
    ElMessage.error('获取标签列表失败');
    console.error(error);
  } finally {
    loading.tags = false;
  }
};

onMounted(() => {
  fetchCategories();
  fetchTags();
});

// --- 分类操作 ---
const handleOpenCategoryDialog = (category = null) => {
  if (category) {
    isEditMode.category = true;
    forms.category = { ...category };
  } else {
    isEditMode.category = false;
    forms.category = { id: null, name: '', slug: '', parent_id: null };
  }
  dialogVisible.category = true;
};

const handleSaveCategory = async () => {
  saving.category = true;
  try {
    const payload = { ...forms.category };
    if (isEditMode.category) {
      await api.updateCategory(payload.id, payload);
    } else {
      await api.createCategory(payload);
    }
    ElMessage.success('保存成功');
    dialogVisible.category = false;
    fetchCategories(); // 重新加载列表
  } catch (error) {
    const errMsg = error.response?.data?.message || '保存失败';
    ElMessage.error(errMsg);
    console.error(error);
  } finally {
    saving.category = false;
  }
};

// --- 标签操作 ---
const handleOpenTagDialog = (tag = null) => {
  if (tag) {
    isEditMode.tag = true;
    forms.tag = { ...tag };
  } else {
    isEditMode.tag = false;
    forms.tag = { id: null, name: '', slug: '' };
  }
  dialogVisible.tag = true;
};

const handleSaveTag = async () => {
  saving.tag = true;
  try {
    const payload = { ...forms.tag };
    if (isEditMode.tag) {
      await api.updateTag(payload.id, payload);
    } else {
      await api.createTag(payload);
    }
    ElMessage.success('保存成功');
    dialogVisible.tag = false;
    fetchTags(); // 重新加载列表
  } catch (error) {
    const errMsg = error.response?.data?.message || '保存失败';
    ElMessage.error(errMsg);
    console.error(error);
  } finally {
    saving.tag = false;
  }
};

// --- 通用删除操作 ---
const handleDelete = (type, id) => {
  ElMessageBox.confirm(
    `确定要删除这个${type === 'category' ? '分类' : '标签'}吗？此操作不可恢复。`,
    '警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      if (type === 'category') {
        await api.deleteCategory(id);
        fetchCategories();
      } else {
        await api.deleteTag(id);
        fetchTags();
      }
      ElMessage.success('删除成功');
    } catch (error) {
      const errMsg = error.response?.data?.message || '删除失败';
      ElMessage.error(errMsg);
      console.error(error);
    }
  }).catch(() => {
    // 用户取消
  });
};
</script>

<style scoped>
.taxonomy-admin-page {
  padding: 20px;
}
.toolbar {
  margin-bottom: 16px;
  text-align: right;
}
</style>