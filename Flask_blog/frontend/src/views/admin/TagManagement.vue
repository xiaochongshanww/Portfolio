<template>
  <div class="tag-management">
    <AdminPageHeader title="标签管理" description="维护文章标签并控制标签库质量。">
      <button type="button" class="primary-btn" @click="showCreateDialog">＋ 新建标签</button>
    </AdminPageHeader>

    <!-- Summary Strip(05 §17 标签语义) -->
    <AdminSummaryStrip :items="summaryItems" />

    <!-- Toolbar:搜索 + 排序 | 未使用清理(danger 低频) -->
    <AdminToolbar
      v-model:search="searchKeyword"
      search-placeholder="搜索标签名称或 slug"
      :result-count="error ? null : filteredTags.length"
      refreshable
      @update:search="() => {}"
      @refresh="loadData"
    >
      <template #filters>
        <select v-model="sortBy" class="adm-select" aria-label="排序方式">
          <option value="usage_desc">按使用量降序</option>
          <option value="usage_asc">按使用量升序</option>
          <option value="name_asc">按名称升序</option>
          <option value="name_desc">按名称降序</option>
          <option value="created_desc">按创建时间</option>
        </select>
      </template>
      <template #right>
        <button type="button" class="ghost-danger-btn" @click="cleanUnusedTags">
          清理未使用 ({{ stats.unused_tags }})
        </button>
      </template>
    </AdminToolbar>

    <section class="table-card">
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="标签数据加载失败"
        compact
        @reload="loadData"
      />
      <AdminStateBlock
        v-else-if="!loading && !filteredTags.length"
        kind="empty"
        title="暂无标签"
        :description="searchKeyword ? '没有匹配的标签,换个关键词试试。' : '创建第一个标签,为文章建立局部标识。'"
        compact
      >
        <button v-if="!searchKeyword" type="button" class="primary-btn" @click="showCreateDialog">＋ 新建标签</button>
      </AdminStateBlock>

      <div v-else class="table-wrap">
        <el-table :data="filteredTags" row-key="id" class="adm-table">
          <el-table-column label="标签" min-width="180">
            <template #default="{ row }">
              <AdminTag :label="row.name" tone="blue" />
            </template>
          </el-table-column>
          <el-table-column label="Slug" min-width="160">
            <template #default="{ row }">
              <code class="slug-code">{{ row.slug }}</code>
            </template>
          </el-table-column>
          <el-table-column label="使用量" width="90" sortable :sort-method="byUsage">
            <template #default="{ row }">
              <span class="num">{{ row.article_count || 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column width="150" fixed="right" align="right">
            <template #default="{ row }">
              <AdminActionMenu :test-id="`tag-${row.id}`">
                <button type="button" class="edit-btn" @click="showEditDialog(row)">编辑</button>
                <template #menu>
                  <el-dropdown-item divided danger :disabled="(row.article_count || 0) > 0" @click="handleDelete(row)">
                    删除标签
                  </el-dropdown-item>
                </template>
              </AdminActionMenu>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-footer">
        <span>共 {{ filteredTags.length }} 个标签</span>
        <span class="foot-note">使用中的标签不可删除</span>
      </div>
    </section>

    <TagEditDialog
      :visible="dialogVisible"
      :mode="dialogMode"
      :tag="editingTag"
      :loading="submitting"
      @update:visible="dialogVisible = $event"
      @confirm="handleSubmit"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';
import AdminSummaryStrip from '../../components/admin/AdminSummaryStrip.vue';
import AdminToolbar from '../../components/admin/AdminToolbar.vue';
import AdminActionMenu from '../../components/admin/AdminActionMenu.vue';
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue';
import AdminTag from '../../components/admin/AdminTag.vue';
import TagEditDialog from '../../components/admin/TagEditDialog.vue';

const loading = ref(false);
const error = ref(false);
const submitting = ref(false);
const dialogVisible = ref(false);
const dialogMode = ref('create');
/** @type {import('vue').Ref<number | null>} */
const editingId = ref(null);
/** @type {import('vue').Ref<any>} */
const editingTag = ref(null);
const searchKeyword = ref('');
const sortBy = ref('usage_desc');
/** @type {import('vue').Ref<any[]>} */
const tags = ref([]);

const stats = reactive({ total_tags: 0, tags_with_articles: 0, unused_tags: 0 });

const summaryItems = computed(() => [
  { label: '全部标签', value: stats.total_tags, note: '当前标签库' },
  { label: '已使用', value: stats.tags_with_articles, note: '至少关联 1 篇' },
  { label: '未使用', value: stats.unused_tags, note: '可考虑清理' },
  { label: '当前显示', value: filteredTags.value.length, note: '经搜索过滤' },
]);

const filteredTags = computed(() => {
  /** @type {any[]} */
  let filtered = [...tags.value];
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase();
    filtered = filtered.filter(
      (tag) =>
        tag.name.toLowerCase().includes(keyword) ||
        (tag.slug || '').toLowerCase().includes(keyword),
    );
  }
  filtered.sort((a, b) => {
    switch (sortBy.value) {
      case 'usage_desc': return (b.article_count || 0) - (a.article_count || 0);
      case 'usage_asc': return (a.article_count || 0) - (b.article_count || 0);
      case 'name_asc': return a.name.localeCompare(b.name);
      case 'name_desc': return b.name.localeCompare(a.name);
      case 'created_desc':
      default: return b.id - a.id;
    }
  });
  return filtered;
});

/** el-table 列排序入口 */
/** @param {any} a @param {any} b */
function byUsage(a, b) {
  return (a.article_count || 0) - (b.article_count || 0);
}

async function loadData() {
  if (loading.value) return;
  loading.value = true;
  error.value = false;
  try {
    const response = await API.getTaxonomyStats();
    if (response.data.code === 0) {
      const data = response.data.data;
      tags.value = data.tags;
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

function showCreateDialog() {
  dialogMode.value = 'create';
  editingId.value = null;
  editingTag.value = null;
  dialogVisible.value = true;
}

/** @param {any} tag */
function showEditDialog(tag) {
  dialogMode.value = 'edit';
  editingId.value = tag.id;
  editingTag.value = tag;
  dialogVisible.value = true;
}

/** @param {{ name: string, slug?: string }} data */
async function handleSubmit(data) {
  submitting.value = true;
  try {
    let response;
    if (dialogMode.value === 'create') {
      response = await API.createTag(data);
    } else {
      response = await API.updateTag(editingId.value, data);
    }
    if (response.data.code === 0) {
      ElMessage.success(dialogMode.value === 'create' ? '标签创建成功' : '标签更新成功');
      dialogVisible.value = false;
      await loadData();
    } else {
      ElMessage.error(response.data.message || '操作失败');
    }
  } catch (e) {
    const err = /** @type {{ response?: { status?: number, data?: { message?: string } } }} */ (e);
    let errorMessage = '操作失败';
    if (err.response?.status === 401) {
      errorMessage = '认证失败，请重新登录';
    } else if (err.response?.status === 403) {
      errorMessage = '权限不足，需要编辑者或管理员权限';
    } else if (err.response?.status === 409) {
      errorMessage = '标签名称或 Slug 已存在，请使用其他名称';
    } else if (err.response?.data?.message) {
      errorMessage = err.response.data.message;
    }
    ElMessage({ message: errorMessage, type: 'error', duration: 5000, showClose: true });
  } finally {
    submitting.value = false;
  }
}

/** @param {any} tag */
async function handleDelete(tag) {
  if ((tag.article_count || 0) > 0) {
    ElMessage.warning('该标签还在使用中，无法删除');
    return;
  }
  try {
    await ElMessageBox.confirm(`删除标签「${tag.name}」?删除后不可恢复。`, '删除标签', {
      type: 'warning',
      confirmButtonText: '删除标签',
      cancelButtonText: '取消',
    });
    const response = await API.deleteTag(tag.id);
    if (response.data.code === 0) {
      ElMessage.success(`标签「${tag.name}」已删除`);
      await loadData();
    } else {
      ElMessage.error(response.data.message || '删除失败');
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败');
  }
}

// 清理未使用的标签
async function cleanUnusedTags() {
  const unusedTags = tags.value.filter((tag) => (tag.article_count || 0) === 0);
  if (unusedTags.length === 0) {
    ElMessage.info('没有未使用的标签');
    return;
  }
  try {
    await ElMessageBox.confirm(
      `将删除 ${unusedTags.length} 个未使用的标签,删除后不可恢复。`,
      '清理未使用标签',
      { type: 'warning', confirmButtonText: '确认清理', cancelButtonText: '取消' },
    );
    for (const tag of unusedTags) {
      await API.deleteTag(tag.id);
    }
    ElMessage.success(`已清理 ${unusedTags.length} 个未使用的标签`);
    await loadData();
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('清理失败');
  }
}

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.tag-management {
  width: 100%;
}
.tag-management :deep(.admin-toolbar) {
  border-bottom: 0;
}
.tag-management :deep(.el-table) {
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

.adm-select {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 12px;
  outline: none;
}
.adm-select:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
}

.ghost-danger-btn {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-control);
  background: var(--adm-surface);
  color: var(--adm-danger);
  font-size: 12px;
  cursor: pointer;
}
.ghost-danger-btn:hover {
  border-color: var(--adm-danger);
  background: var(--adm-danger-soft);
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

.slug-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  color: var(--adm-muted);
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
</style>
