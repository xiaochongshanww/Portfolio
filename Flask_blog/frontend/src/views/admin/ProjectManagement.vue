<template>
  <div class="project-management">
    <div class="page-head">
      <h2>项目管理</h2>
      <el-button type="primary" @click="openCreate">新建项目</el-button>
    </div>

    <el-table :data="projects" v-loading="loading" border stripe>
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="slug" label="Slug" min-width="120" />
      <el-table-column prop="tag" label="分类" width="90" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : row.status === 'paused' ? 'warning' : 'info'" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="当前" width="60" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_current" type="danger" size="small" effect="plain">是</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序" width="60" align="center" />
      <el-table-column prop="updated_at" label="更新时间" width="150">
        <template #default="{ row }">{{ shortDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="warning" plain @click="toggleCurrent(row)">
            {{ row.is_current ? '取消当前' : '设为当前' }}
          </el-button>
          <el-button size="small" type="danger" plain :disabled="!isAdmin" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑项目' : '新建项目'" width="640px">
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
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 项目管理(P2-A1 验收:模型注册进 admin 可管理)
 * 基础 CRUD + is_current 切换;JSON 字段以文本编辑,保存前校验。
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { API } from '../../api'
import { useUserStore } from '../../stores/user'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.hasRole(['admin']))

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
/** @type {import('vue').Ref<any[]>} */
const projects = ref([])

/** @type {Record<string,string>} */
const STATUS = { active: '开发中', paused: '暂停', archived: '已归档' }
/** @param {string} s */
function statusLabel(s) {
  return STATUS[s] || s
}

const previewPlaceholder = computed(() =>
  form.value.preview_type === 'image'
    ? "图片:填 {\"url\":\"/uploads/x.png\",\"alt\":\"说明\"}"
    : "SVG:填 {\"svg\":\"<svg>…</svg>\"}",
)

/** @param {string | undefined} s */
function shortDate(s) {
  if (!s) return ''
  return s.replace('T', ' ').slice(0, 16)
}

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
  try {
    const resp = await API.adminListProjects()
    projects.value = resp?.data?.data?.list || []
  } catch (e) {
    ElMessage.error('项目列表加载失败')
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

/** @param {string} text @param {string} what */
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
    await ElMessageBox.confirm(`确定删除项目「${row.name}」?此操作不可恢复。`, '删除确认', { type: 'warning' })
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
  padding: 4px;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-head h2 {
  margin: 0;
  font-size: 18px;
}
</style>
