<template>
  <div class="project-management">
    <AdminPageHeader title="项目管理" description="维护项目状态、展示信息和关联文章。">
      <button type="button" class="primary-btn" @click="openCreate">＋ 新建项目</button>
    </AdminPageHeader>

    <!-- Summary Strip(05 §18 项目语义) -->
    <AdminSummaryStrip :items="summaryItems" />

    <!-- Toolbar:搜索 + 状态筛选 | 结果数/刷新 -->
    <AdminToolbar
      v-model:search="search"
      search-placeholder="搜索项目名称或描述"
      :result-count="error ? null : filteredProjects.length"
      refreshable
      @update:search="() => {}"
      @refresh="load"
    >
      <template #filters>
        <select v-model="statusFilter" class="adm-select" aria-label="按状态筛选">
          <option value="">全部状态</option>
          <option value="active">开发中</option>
          <option value="paused">暂停</option>
          <option value="archived">已归档</option>
        </select>
      </template>
    </AdminToolbar>

    <section class="table-card">
      <AdminStateBlock
        v-if="error"
        kind="error"
        title="项目列表加载失败"
        compact
        @reload="load"
      />
      <AdminStateBlock
        v-else-if="!loading && !filteredProjects.length"
        kind="empty"
        title="暂无项目"
        :description="search || statusFilter ? '当前筛选条件下没有项目。' : '录入第一个项目,展示你正在做的东西。'"
        compact
      >
        <button v-if="!search && !statusFilter" type="button" class="primary-btn" @click="openCreate">＋ 新建项目</button>
      </AdminStateBlock>

      <div v-else class="table-wrap">
        <el-table :data="filteredProjects" row-key="id" class="adm-table">
          <el-table-column label="项目" min-width="240">
            <template #default="{ row }">
              <div class="proj-name">{{ row.name }}</div>
              <div v-if="row.description" class="proj-desc">{{ row.description }}</div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <AdminStatus :kind="statusKind(row.status)" :label="statusLabel(row.status)" />
            </template>
          </el-table-column>
          <el-table-column label="技术栈" min-width="160">
            <template #default="{ row }">
              <div class="tech-stack">
                <AdminTag v-for="t in techOf(row)" :key="t" :label="t" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="当前" width="70" align="center">
            <template #default="{ row }">
              <span v-if="row.is_current" class="current-flag">●</span>
              <span v-else class="cell-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="最近更新" width="110">
            <template #default="{ row }">
              <span class="cell-text">{{ shortDate(row.updated_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column width="150" fixed="right" align="right">
            <template #default="{ row }">
              <AdminActionMenu :test-id="`project-${row.id}`">
                <button type="button" class="edit-btn" @click="openEdit(row)">编辑</button>
                <template #menu>
                  <el-dropdown-item @click="toggleCurrent(row)">
                    {{ row.is_current ? '取消当前' : '设为当前' }}
                  </el-dropdown-item>
                  <el-dropdown-item divided danger :disabled="!isAdmin" @click="remove(row)">
                    删除项目
                  </el-dropdown-item>
                </template>
              </AdminActionMenu>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-footer">
        <span>共 {{ filteredProjects.length }} 个项目</span>
        <span class="foot-note">同一时间只有一个当前重点项目</span>
      </div>
    </section>

    <!-- 创建/编辑对话框(05 §26:超过简单表单改 Drawer 是后续优化,当前沿用 Dialog) -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑项目' : '新建项目'"
      width="640px"
    >
      <el-form :model="form" label-width="110px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="Slug" required><el-input v-model="form.slug" placeholder="url 标识,如 structure-lab" /></el-form-item>
        <el-form-item label="一句话描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="分类标签"><el-input v-model="form.tag" placeholder="内部工具 / 实验 / 工具" /></el-form-item>
        <el-form-item label="技术栈"><el-input v-model="form.techStack" placeholder="逗号分隔,如 Vue, Canvas" /></el-form-item>
        <el-row>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status">
                <el-option label="开发中" value="active" />
                <el-option label="暂停" value="paused" />
                <el-option label="归档" value="archived" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="排序">
              <el-input-number v-model="form.sort_order" :min="0" :max="999" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row>
          <el-col :span="12">
            <el-form-item label="预览类型">
              <el-select v-model="form.preview_type">
                <el-option label="无" value="none" />
                <el-option label="图片" value="image" />
                <el-option label="SVG" value="svg" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="当前重点项目">
              <el-switch v-model="form.is_current" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="form.preview_type !== 'none'" label="预览数据 JSON">
          <el-input v-model="form.previewData" type="textarea" :rows="2" :placeholder="previewPlaceholder" />
        </el-form-item>
        <el-form-item label="Demo 链接"><el-input v-model="form.link_url" placeholder="https://…" /></el-form-item>
        <el-form-item label="Repo 链接"><el-input v-model="form.repo_url" placeholder="https://github.com/…" /></el-form-item>
        <el-form-item label="为什么做"><el-input v-model="form.motivation" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="现在做到哪里"><el-input v-model="form.progress" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="关键设计决策"><el-input v-model="form.design_notes" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="相关文章 slug"><el-input v-model="form.relatedSlugs" placeholder="逗号分隔,如 rag-intro, jwt-basics" /></el-form-item>
        <el-form-item label="Changelog JSON">
          <el-input v-model="form.changelog" type="textarea" :rows="3"
            placeholder='[{"date":"2026-08-20","title":"…","text":"…"},{"date":"…","text":"…","next":true}]' />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 项目管理(P2-A1 + 2026 Pattern 迁移)
 * Governance List Pattern;is_current 唯一性由后端 service 保证。
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { API } from '../../api'
import { useUserStore } from '../../stores/user'
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue'
import AdminSummaryStrip from '../../components/admin/AdminSummaryStrip.vue'
import AdminToolbar from '../../components/admin/AdminToolbar.vue'
import AdminStatus from '../../components/admin/AdminStatus.vue'
import AdminActionMenu from '../../components/admin/AdminActionMenu.vue'
import AdminStateBlock from '../../components/admin/AdminStateBlock.vue'
import AdminTag from '../../components/admin/AdminTag.vue'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.hasRole(['admin']))

const loading = ref(false)
const error = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const search = ref('')
const statusFilter = ref('')
/** @type {import('vue').Ref<any[]>} */
const projects = ref([])

/** @type {Record<string,string>} */
const STATUS = { active: '开发中', paused: '暂停', archived: '已归档' }

/** @param {string} s */
function statusLabel(s) {
  return STATUS[s] || s
}

/** @param {string} s @returns {'success'|'warning'|'neutral'} */
function statusKind(s) {
  switch (s) {
    case 'active': return 'warning' // 开发中=活跃进行
    case 'paused': return 'neutral'
    default: return 'neutral'
  }
}

const filteredProjects = computed(() => {
  let list = projects.value
  const kw = search.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(
      (p) =>
        String(p.name || '').toLowerCase().includes(kw) ||
        String(p.description || '').toLowerCase().includes(kw),
    )
  }
  if (statusFilter.value) {
    list = list.filter((p) => p.status === statusFilter.value)
  }
  return list
})

const summaryItems = computed(() => [
  { label: '全部项目', value: projects.value.length, note: '公开 + 归档' },
  { label: '开发中', value: projects.value.filter((p) => p.status === 'active').length, note: '进行中' },
  { label: '当前重点', value: projects.value.filter((p) => p.is_current).length, note: '首页大区展示' },
  { label: '已归档', value: projects.value.filter((p) => p.status === 'archived').length, note: '历史项目' },
])

/** @param {any} p */
function techOf(p) {
  return Array.isArray(p.tech_stack) ? p.tech_stack : []
}

/** @param {string | undefined} s */
function shortDate(s) {
  if (!s) return '—'
  return s.replace('T', ' ').slice(0, 10)
}

const previewPlaceholder = computed(() =>
  form.value.preview_type === 'image'
    ? "图片:填 {\"url\":\"/uploads/x.png\",\"alt\":\"说明\"}"
    : "SVG:填 {\"svg\":\"<svg>…</svg>\"}",
)

const emptyForm = () => ({
  name: '', slug: '', description: '', tag: '', techStack: '',
  status: 'active', is_current: false, preview_type: 'none', previewData: '',
  link_url: '', repo_url: '', motivation: '', progress: '', design_notes: '',
  relatedSlugs: '', changelog: '', sort_order: 0,
})
/** @type {import('vue').Ref<ReturnType<typeof emptyForm>>} */
const form = ref(emptyForm())

async function load() {
  loading.value = true
  error.value = false
  try {
    const resp = await API.adminListProjects()
    projects.value = resp?.data?.data?.list || []
  } catch (e) {
    error.value = true
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  dialogVisible.value = true
}

/** @param {any} row */
function openEdit(row) {
  editingId.value = row.id
  form.value = {
    name: row.name || '',
    slug: row.slug || '',
    description: row.description || '',
    tag: row.tag || '',
    techStack: (row.tech_stack || []).join(', '),
    status: row.status || 'active',
    is_current: !!row.is_current,
    preview_type: row.preview_type || 'none',
    previewData: row.preview_data ? JSON.stringify(row.preview_data) : '',
    link_url: row.link_url || '',
    repo_url: row.repo_url || '',
    motivation: row.motivation || '',
    progress: row.progress || '',
    design_notes: row.design_notes || '',
    relatedSlugs: (row.related_article_slugs || []).join(', '),
    changelog: (row.changelog && row.changelog.length) ? JSON.stringify(row.changelog) : '',
    sort_order: row.sort_order || 0,
  }
  dialogVisible.value = true
}

/** @param {string} text @param {string} what @returns {any} undefined 表示解析失败 */
function parseJson(text, what) {
  if (!text.trim()) return null
  try {
    return JSON.parse(text)
  } catch (e) {
    ElMessage.error(`${what} 不是合法 JSON`)
    return undefined
  }
}

async function save() {
  if (!form.value.name.trim() || !form.value.slug.trim()) {
    ElMessage.error('name 与 slug 必填')
    return
  }
  const previewData = parseJson(form.value.previewData, '预览数据')
  if (previewData === undefined) return
  const changelog = parseJson(form.value.changelog, 'Changelog')
  if (changelog === undefined) return

  const payload = {
    name: form.value.name.trim(),
    slug: form.value.slug.trim(),
    description: form.value.description || null,
    tag: form.value.tag || null,
    tech_stack: form.value.techStack.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
    status: form.value.status,
    is_current: form.value.is_current,
    preview_type: form.value.preview_type,
    preview_data: previewData,
    link_url: form.value.link_url || null,
    repo_url: form.value.repo_url || null,
    motivation: form.value.motivation || null,
    progress: form.value.progress || null,
    design_notes: form.value.design_notes || null,
    related_article_slugs: form.value.relatedSlugs.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
    changelog: changelog || [],
    sort_order: form.value.sort_order,
  }
  saving.value = true
  try {
    if (editingId.value) await API.updateProject(editingId.value, payload)
    else await API.createProject(payload)
    ElMessage.success('已保存')
    dialogVisible.value = false
    await load()
  } catch (e) {
    const err = /** @type {{response?: {data?: {message?: string}}}} */ (e)
    ElMessage.error(err?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

/** @param {any} row */
async function toggleCurrent(row) {
  try {
    await API.updateProject(row.id, { is_current: !row.is_current })
    ElMessage.success(row.is_current ? '已取消当前项目' : '已设为当前项目(其它项目自动取消)')
    await load()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

/** @param {any} row */
async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `删除项目「${row.name}」?删除后不可恢复。`,
      '删除项目',
      { type: 'warning', confirmButtonText: '删除项目', cancelButtonText: '取消' },
    )
  } catch (e) {
    return
  }
  try {
    await API.deleteProject(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.project-management {
  width: 100%;
}
.project-management :deep(.admin-toolbar) {
  border-bottom: 0;
}
.project-management :deep(.el-table) {
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
  font-size: 13px;
  outline: none;
}
.adm-select:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px var(--adm-primary-soft);
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

.proj-name {
  font-size: 13px;
  font-weight: 680;
  color: var(--adm-text);
}
.proj-desc {
  margin-top: 4px;
  font-size: 12px;
  color: var(--adm-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tech-stack {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}
.current-flag {
  color: var(--adm-primary);
  font-size: 12px;
}
.cell-muted {
  color: var(--adm-muted-light);
}
.cell-text {
  font-size: 13px;
  color: var(--adm-text-2);
  font-variant-numeric: tabular-nums;
}

.edit-btn {
  height: 29px;
  padding: 0 9px;
  border: 1px solid var(--adm-border);
  border-radius: 7px;
  background: var(--adm-surface);
  color: var(--adm-text-2);
  font-size: 13px;
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
  font-size: 12px;
}
.foot-note {
  font-size: 12px;
  color: var(--adm-muted-light);
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
