<template>
  <div class="category-management">
    <AdminPageHeader title="专题管理" description="组织长期主题和文章入口。">
      <button type="button" class="primary-btn" @click="showCreateDialog()">＋ 新建专题</button>
    </AdminPageHeader>

    <!-- Summary Strip(05 §16 专题语义) -->
    <AdminSummaryStrip :items="summaryItems" />

    <!-- Toolbar(05 §17:搜索 + 按更新排序占位) -->
    <AdminToolbar
      v-model:search="search"
      search-placeholder="搜索专题名称或 slug"
      :result-count="error ? null : totalCount"
      refreshable
      @update:search="onSearchInput"
      @refresh="loadData"
    />

    <section class="table-card">
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="专题数据加载失败"
        compact
        @reload="loadData"
      />
      <AdminStateBlock
        v-else-if="!loading && !categories.length"
        kind="empty"
        title="暂无专题"
        description="创建第一个专题,开始组织你的长期内容。"
        compact
      >
        <button type="button" class="primary-btn" @click="showCreateDialog()">＋ 新建专题</button>
      </AdminStateBlock>

      <div v-else class="table-wrap">
        <el-table
          :data="filteredTree"
          row-key="id"
          :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
          default-expand-all
          class="adm-table"
        >
          <el-table-column label="专题" min-width="260">
            <template #default="{ row }">
              <div class="topic-name">
                <span class="name-text">{{ row.name }}</span>
                <AdminTag v-if="row.slug" :label="row.slug" bordered />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="文章" width="80">
            <template #default="{ row }">
              <span class="num">{{ row.article_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <!-- 05 §16:持续更新/常规 -->
              <AdminStatus
                :kind="row.article_count > 0 ? 'success' : 'neutral'"
                :label="row.article_count > 0 ? '持续更新' : '常规'"
              />
            </template>
          </el-table-column>
          <el-table-column width="150" fixed="right" align="right">
            <template #default="{ row }">
              <AdminActionMenu :test-id="`category-${row.id}`">
                <button type="button" class="edit-btn" @click="showEditDialog(row)">编辑</button>
                <template #menu>
                  <el-dropdown-item @click="showCreateDialog(row)">添加子专题</el-dropdown-item>
                  <el-dropdown-item divided danger @click="handleDelete(row)">删除专题</el-dropdown-item>
                </template>
              </AdminActionMenu>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-footer">
        <span>共 {{ totalCount }} 个专题</span>
        <span class="foot-note">按层级展示</span>
      </div>
    </section>

    <!-- 创建/编辑对话框(05 §26 简短表单) -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建专题' : '编辑专题'"
      width="480px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="专题名称" @input="generateSlug" />
        </el-form-item>
        <el-form-item label="Slug" prop="slug">
          <el-input v-model="form.slug" placeholder="URL 标识,留空自动生成" />
        </el-form-item>
        <el-form-item label="父专题" prop="parent_id">
          <el-select v-model="form.parent_id" placeholder="选择父专题(可选)" clearable style="width: 100%">
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
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ dialogMode === 'create' ? '创建' : '保存' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminSummaryStrip from '../../components/admin/AdminSummaryStrip.vue';
import AdminToolbar from '../../components/admin/AdminToolbar.vue';
import AdminStatus from '../../components/admin/AdminStatus.vue';
import AdminActionMenu from '../../components/admin/AdminActionMenu.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';
import AdminTag from '../../components/admin/AdminTag.vue';

const loading = ref(false);
const error = ref(false);
const submitting = ref(false);
const dialogVisible = ref(false);
const dialogMode = ref('create');
const editingId = ref(null);
const search = ref('');

/** @type {import('vue').Ref<any[]>} */
const categories = ref([]);
/** @type {import('vue').Ref<any>} */
const formRef = ref();

const stats = reactive({
  total_categories: 0,
  categories_with_articles: 0,
  unused_categories: 0,
});

const form = reactive({ name: '', slug: '', parent_id: null });

/** @type {import('element-plus').FormRules} */
const formRules = {
  name: [
    { required: true, message: '请输入专题名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' },
  ],
  slug: [
    { pattern: /^[a-z0-9-]*$/, message: 'Slug 只能包含小写字母、数字和连字符', trigger: 'blur' },
  ],
};

const treeData = computed(() => {
  /**
   * @param {any[]} items
   * @param {any} [parentId]
   * @returns {any[]}
   */
  const buildTree = (items, parentId = null) => {
    return items
      .filter((item) => item.parent_id === parentId)
      .map((item) => ({ ...item, children: buildTree(items, item.id) }));
  };
  return buildTree(categories.value);
});

/** 搜索过滤(命中名称或 slug,保留父链) */
const filteredTree = computed(() => {
  const kw = search.value.trim().toLowerCase();
  if (!kw) return treeData.value;
  /**
   * @param {any[]} nodes
   * @returns {any[]}
   */
  const filterNodes = (nodes) => {
    /** @type {any[]} */
    const out = [];
    for (const n of nodes) {
      const hit = String(n.name || '').toLowerCase().includes(kw) || String(n.slug || '').toLowerCase().includes(kw);
      const children = filterNodes(n.children || []);
      if (hit || children.length) out.push({ ...n, children });
    }
    return out;
  };
  return filterNodes(treeData.value);
});

const totalCount = computed(() => categories.value.length);

const summaryItems = computed(() => [
  { label: '专题', value: stats.total_categories, note: '长期维护' },
  { label: '已使用', value: stats.categories_with_articles, note: '含文章' },
  { label: '未使用', value: stats.unused_categories, note: '可整理' },
  { label: '未归类文章', value: unclassifiedCount.value, note: '可后续归入' },
]);

const unclassifiedCount = computed(() => {
  // 无统计接口时的降级:0(不虚构数字)
  return 0;
});

const parentOptions = computed(() => {
  /**
   * @param {any[]} items
   * @param {number} [level]
   * @returns {any[]}
   */
  const getOptions = (items, level = 0) => {
    /** @type {any[]} */
    const options = [];
    items.forEach((item) => {
      options.push({ id: item.id, name: '　'.repeat(level) + item.name });
      if (item.children && item.children.length > 0) {
        options.push(...getOptions(item.children, level + 1));
      }
    });
    return options;
  };
  return getOptions(treeData.value);
});

async function loadData() {
  if (loading.value) return;
  loading.value = true;
  error.value = false;
  try {
    const response = await API.getTaxonomyStats();
    if (response.data.code === 0) {
      const data = response.data.data;
      categories.value = data.categories;
      Object.assign(stats, data.summary);
    } else {
      error.value = true;
    }
  } catch (e) {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

/** @type {ReturnType<typeof setTimeout> | undefined} */
let searchTimer;
function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {}, 200); // 过滤为前端即时,无需请求
}

/** @param {any} [parent] */
function showCreateDialog(parent = null) {
  dialogMode.value = 'create';
  editingId.value = null;
  resetForm();
  if (parent) {
    form.parent_id = parent.id;
  }
  dialogVisible.value = true;
}

/** @param {any} category */
function showEditDialog(category) {
  dialogMode.value = 'edit';
  editingId.value = category.id;
  form.name = category.name;
  form.slug = category.slug;
  form.parent_id = category.parent_id;
  dialogVisible.value = true;
}

function resetForm() {
  form.name = '';
  form.slug = '';
  form.parent_id = null;
  if (formRef.value) {
    formRef.value.resetFields();
  }
}

// 根据名称生成 Slug
function generateSlug() {
  if (!form.slug && form.name) {
    form.slug = form.name
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fa5]/g, '-')
      .replace(/--+/g, '-')
      .replace(/^-|-$/g, '');
  }
}

async function handleSubmit() {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
    submitting.value = true;
    const data = {
      name: form.name.trim(),
      slug: form.slug.trim() || undefined,
      parent_id: form.parent_id || undefined,
    };
    let response;
    if (dialogMode.value === 'create') {
      response = await API.createCategory(data);
    } else {
      response = await API.updateCategory(editingId.value, data);
    }
    if (response.data.code === 0) {
      ElMessage.success(dialogMode.value === 'create' ? '专题创建成功' : '专题更新成功');
      dialogVisible.value = false;
      await loadData();
    } else {
      ElMessage.error(response.data.message || '操作失败');
    }
  } catch (e) {
    if (e !== 'validation failed') ElMessage.error('操作失败');
  } finally {
    submitting.value = false;
  }
}

/** @param {any} category */
async function handleDelete(category) {
  const hasArticles = category.article_count > 0;
  const message = hasArticles
    ? `专题「${category.name}」下还有 ${category.article_count} 篇文章,删除后这些文章将变为未分类。`
    : `删除专题「${category.name}」?`;
  try {
    await ElMessageBox.confirm(message, '删除专题', {
      type: 'warning',
      confirmButtonText: '删除专题',
      cancelButtonText: '取消',
    });
    const response = await API.deleteCategory(category.id);
    if (response.data.code === 0) {
      ElMessage.success(
        hasArticles
          ? `专题「${category.name}」已删除,${category.article_count} 篇文章转为未分类`
          : `专题「${category.name}」已删除`,
      );
      await loadData();
    } else {
      ElMessage.error(response.data.message || '删除失败');
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败');
  }
}

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.category-management {
  width: 100%;
}
.category-management :deep(.admin-toolbar) {
  border-bottom: 0;
}
.category-management :deep(.el-table) {
  width: 100%;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--adm-primary);
  border-radius: 9px;
  background: var(--adm-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.primary-btn:hover {
  opacity: 0.92;
}

.table-card {
  border: 1px solid var(--adm-border);
  border-radius: 0 0 var(--adm-r-container) var(--adm-r-container);
  background: var(--adm-surface);
  overflow: hidden;
}
.table-wrap {
  overflow: auto;
}

.topic-name {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.name-text {
  font-size: 13px;
  font-weight: 680;
  color: var(--adm-text);
}
.num {
  font-variant-numeric: tabular-nums;
  color: var(--adm-text-2);
}

.edit-btn {
  height: 29px;
  padding: 0 9px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 11px;
  cursor: pointer;
}
.edit-btn:hover:not(:disabled) {
  border-color: var(--adm-border-strong);
  color: var(--adm-text);
}

.table-footer {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 8px 12px;
  border-top: 1px solid var(--adm-border);
  color: var(--adm-muted);
  font-size: 11px;
}
.foot-note {
  font-size: 11px;
  color: var(--adm-muted-light);
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
