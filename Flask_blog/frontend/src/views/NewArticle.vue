<template>
  <div class="editor-page shell">
    <!-- 页头 + 三键(05 §25:Save Draft / Preview / Publish) -->
    <header class="editor-top">
      <div class="head-copy">
        <div class="eyebrow">创作中心</div>
        <h1 class="page-title">{{ isEditMode ? '编辑文章' : '创作新文章' }}</h1>
        <p class="page-subtitle">发布后将进入审核队列,审核通过即公开。</p>
      </div>
      <div class="head-keys">
        <button
          type="button"
          class="key-btn ghost"
          :disabled="loading || autoSaving"
          @click="saveDraft"
        >
          {{ autoSaving ? '保存中…' : '保存草稿' }}
        </button>
        <button type="button" class="key-btn ghost" :disabled="loading" @click="openPreview">预览</button>
        <button
          type="button"
          class="key-btn primary"
          :disabled="loading || autoSaving"
          @click.prevent="submit"
        >
          {{ loading ? (isEditMode ? '更新中…' : '发布中…') : (isEditMode ? '更新文章' : '发布文章') }}
        </button>
      </div>
    </header>

    <!-- 状态条(错误/提交结果/自动保存) -->
    <div v-if="error" class="editor-alert error">{{ error }}</div>
    <div v-if="success" class="editor-alert warn">
      {{ isEditMode ? '文章已重新提交审核，审核通过后更新发布。' : '文章已提交审核，审核通过后将自动发布。' }}
    </div>
    <div v-if="lastSaveTime || hasUnsavedChanges" class="autosave-strip">
      <span v-if="autoSaving">正在自动保存…</span>
      <span v-else-if="hasUnsavedChanges">有未保存的更改,内容将在 3 秒后自动保存到本地草稿</span>
      <span v-else-if="lastSaveTime">上次保存:{{ formatSaveTime(lastSaveTime) }}</span>
    </div>

    <!-- Main / Side(05 §24) -->
    <div class="editor-grid">
      <main class="editor-main">
        <section class="block">
          <label class="field-label" for="article-title">标题 <i class="req">*</i></label>
          <input
            id="article-title"
            v-model="form.title"
            type="text"
            class="title-input"
            :class="{ 'error-input': formErrors.title }"
            placeholder="请输入吸引人的标题..."
            maxlength="200"
            data-field="title"
            @blur="handleFieldBlur('title', form.title)"
            @input="clearFieldError('title')"
          >
          <div class="field-count">{{ (form.title || '').length }} / 200</div>
          <p v-if="formErrors.title" class="field-error">{{ formErrors.title }}</p>
        </section>

        <section class="block">
          <label class="field-label" for="article-summary">摘要</label>
          <textarea
            id="article-summary"
            v-model="form.summary"
            class="summary-input"
            :class="{ 'error-input': formErrors.summary }"
            rows="3"
            maxlength="500"
            placeholder="简要描述文章内容,帮助读者快速了解..."
            data-field="summary"
            @blur="handleFieldBlur('summary', form.summary)"
            @input="clearFieldError('summary')"
          />
          <div class="field-count">{{ (form.summary || '').length }} / 500</div>
          <p v-if="formErrors.summary" class="field-error">{{ formErrors.summary }}</p>
          <p v-else class="hint">摘要将显示在文章列表中,建议控制在 100-200 字。</p>
        </section>

        <section class="block">
          <label class="field-label">封面</label>
          <CoverImageEditor
            :image="form.featured_image"
            @update:image="form.featured_image = $event"
            @focal-change="onFocal"
          />
        </section>

        <section class="block">
          <label class="field-label">正文 <i class="req">*</i></label>
          <div data-field="content_md" class="content_md-field">
            <VditorEditor ref="blockEditorRef" v-model="form.content_md" />
          </div>
          <p v-if="formErrors.content_md" class="field-error">{{ formErrors.content_md }}</p>
          <div class="kbd-hint">
            <button type="button" class="kbd-btn" @click="showKeyboardShortcuts">快捷键提示 (Ctrl+K)</button>
            <span class="kbd-preview">Ctrl+S 保存草稿 · Ctrl+Enter {{ isEditMode ? '更新' : '发布' }} · F1 帮助</span>
          </div>
        </section>
      </main>

      <aside class="editor-side">
        <section class="side-block">
          <h2>发布状态</h2>
          <div class="status-row">
            <span class="status-label">状态</span>
            <span class="status-value">{{ isEditMode ? '重新提交审核' : '草稿' }}</span>
          </div>
          <div class="status-row">
            <span class="status-label">自动保存</span>
            <span class="status-value">
              <template v-if="autoSaving">保存中…</template>
              <template v-else-if="hasUnsavedChanges">有未保存更改</template>
              <template v-else-if="lastSaveTime">已保存 {{ formatSaveTime(lastSaveTime) }}</template>
              <template v-else>尚未保存</template>
            </span>
          </div>
          <div class="status-row">
            <span class="status-label">可见性</span>
            <span class="status-value">审核通过后公开</span>
          </div>
        </section>

        <section class="side-block">
          <h2>分类 <i v-if="formErrors.category_id" class="req">*</i></h2>
          <CategorySelector
            v-model="form.category_id"
            :categories="categories"
            :article-data="{
              title: form.title,
              content: form.content_md,
              summary: form.summary,
              tags: form.tags_raw ? form.tags_raw.split(',').map(t => t.trim()).filter(Boolean) : []
            }"
            :auto-recommend="true"
            class="side-category"
            @change="handleCategoryChange"
            @recommendation-selected="handleRecommendationSelected"
            @refresh-categories="loadCategories"
          />
          <p v-if="formErrors.category_id" class="field-error">{{ formErrors.category_id }}</p>
          <p v-else class="hint">选择合适分类有助于读者发现文章,支持 AI 推荐。</p>
        </section>

        <section class="side-block">
          <h2>标签</h2>
          <TagManager
            :model-value="selectedTags"
            :available-tags="availableTags.map(t => ({ id: t.id ?? 0, name: t.name ?? '', article_count: t.article_count }))"
            @update:model-value="updateTagsRaw"
          />
        </section>

        <section class="side-block">
          <h2>链接</h2>
          <input
            v-model="form.slug"
            type="text"
            class="side-input"
            :class="{ 'error-input': formErrors.slug }"
            placeholder="custom-article-url"
            data-field="slug"
            @blur="handleFieldBlur('slug', form.slug)"
            @input="clearFieldError('slug')"
          >
          <p v-if="formErrors.slug" class="field-error">{{ formErrors.slug }}</p>
          <p v-else class="hint">自定义 URL 路径,留空自动生成。</p>
        </section>

        <section class="side-block">
          <h2>SEO</h2>
          <SEOFields
            :seo-title="form.seo_title"
            :seo-desc="form.seo_desc"
            @update:seo-title="form.seo_title = $event"
            @update:seo-desc="form.seo_desc = $event"
          />
        </section>

        <section class="side-block">
          <h2>定时发布</h2>
          <SchedulePicker
            :enabled="form.enable_schedule"
            :date="form.scheduled_at"
            @update:enabled="form.enable_schedule = $event"
            @update:date="form.scheduled_at = $event"
          />
        </section>
      </aside>
    </div>

    <!-- 预览由 openPreview 以纯 DOM 挂载(绕开本页慢性 __vnode 补丁缺陷,见 06 §7 遗留) -->
  </div>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { API } from '../api';
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router';
import { useUserStore } from '../stores/user';
import axios from 'axios';
import { setMeta } from '../composables/useMeta';
import { ElMessage, ElMessageBox } from 'element-plus';
import message, { MESSAGE_PRIORITY } from '../utils/message';
import VditorEditor from '../components/VditorEditor.vue';
import CoverImageEditor from '../components/cover/CoverImageEditor.vue';
import CategorySelector from '../components/CategorySelector.vue';
import TagManager from '../components/TagManager.vue';
import SEOFields from '../components/SEOFields.vue';
import SchedulePicker from '../components/SchedulePicker.vue';
import DOMPurify from 'dompurify';
import { renderMarkdown } from '../utils/markdownProcessor.reliable.js';
import { ERROR_CODE_MAP } from '../governance/errorCodes.generated';
/** @typedef {import('../types').Article} Article */
/** @typedef {import('../types').Category} Category */
/**
 * @typedef {{ id?: number, name?: string, article_count?: number }} NewTag
 * @typedef {{ title: string, content_md: string, tags_raw: string, seo_title: string, seo_desc: string, slug: string, summary: string, featured_image: string, featured_focal_x: number | null, featured_focal_y: number | null, enable_schedule: boolean, scheduled_at: string, category_id: number | null }} ArticleForm
 */

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

// 编辑模式状态
const isEditMode = ref(false);
/** @type {import('vue').Ref<number | null>} */
const editingArticleId = ref(null);
/** @type {import('vue').Ref<Article | null>} */
const originalArticle = ref(null);

// 表单状态
/** @type {import('vue').Ref<ArticleForm>} */
const form = ref({ 
  title: '', 
  content_md: '', 
  tags_raw: '', 
  seo_title: '', 
  seo_desc: '', 
  slug: '', 
  summary: '', 
  featured_image: '', 
  featured_focal_x: null, 
  featured_focal_y: null, 
  enable_schedule: false, 
  scheduled_at: '',
  category_id: null // 新增分类字段
});

// 页面状态
const loading = ref(false);
const error = ref('');
const success = ref(false);
/** @type {import('vue').Ref<Category[]>} */
const categories = ref([]);
const categoryLoading = ref(false);

// 标签相关状态
/** @type {import('vue').Ref<NewTag[]>} */
const availableTags = ref([]);
/** @type {import('vue').Ref<string[]>} */
const selectedTags = ref([]);
const tagsLoading = ref(false);

// 导航修复函数 - 简化版本
const handleDraftRestored = () => {
  console.log('📝 草稿恢复事件触发，确保导航状态正常');
  // 简单确认状态重置，不进行复杂操作
  hasUnsavedChanges.value = false;
  isRestoringDraft.value = false;
};

// 预览(05 §25 Preview 键):纯 DOM 全屏遮罩,复用正文管线 renderMarkdown + DOMPurify。
// 不走 Vue Teleport——本页存在慢性 __vnode 补丁缺陷会中止 flush,见 06 §7 遗留事项。
async function openPreview() {
  let html = '';
  try {
    const raw = await renderMarkdown(form.value.content_md || '');
    html = DOMPurify.sanitize(raw);
  } catch (e) {
    html = '<p style="color:#b91c1c">正文渲染失败,请检查内容格式。</p>';
  }

  const overlay = document.createElement('div');
  overlay.className = 'preview-overlay';

  const bar = document.createElement('div');
  bar.className = 'preview-bar';
  const tag = document.createElement('span');
  tag.className = 'preview-tag';
  tag.textContent = '预览';
  const barTitle = document.createElement('span');
  barTitle.className = 'preview-title';
  barTitle.textContent = form.value.title || '未命名文章';
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'preview-close';
  close.textContent = '关闭预览 ×';
  close.addEventListener('click', () => overlay.remove());
  bar.append(tag, barTitle, close);

  const scroll = document.createElement('div');
  scroll.className = 'preview-scroll';
  const canvas = document.createElement('article');
  canvas.className = 'preview-canvas';
  const h1 = document.createElement('h1');
  h1.className = 'preview-h1';
  h1.textContent = form.value.title || '未命名文章';
  const deck = document.createElement('p');
  deck.className = 'preview-deck';
  deck.textContent = form.value.summary || '';
  const body = document.createElement('div');
  body.className = 'preview-body';
  body.innerHTML = html;
  canvas.append(h1, deck, body);
  scroll.append(canvas);
  overlay.append(bar, scroll);

  document.body.appendChild(overlay);
}

// 编辑器引用
/** @type {import('vue').Ref<{ syncContent?: () => string, setContent?: (content: string) => void } | null>} */
const blockEditorRef = ref(null);

// 表单验证状态
/** @type {import('vue').Ref<Record<string, string>>} */
const formErrors = ref({});
const showValidation = ref(false);
const validationRules = {
  title: [
    { required: true, message: '请输入文章标题', trigger: 'blur' },
    { min: 2, max: 200, message: '标题长度应在2-200个字符之间', trigger: 'blur' }
  ],
  content_md: [
    { required: true, message: '请输入文章内容', trigger: 'blur' },
    { min: 1, message: '请输入文章内容', trigger: 'blur' }
  ],
  summary: [
    { max: 500, message: '摘要不能超过500个字符', trigger: 'blur' }
  ],
  seo_title: [
    { max: 60, message: 'SEO标题不能超过60个字符', trigger: 'blur' }
  ],
  seo_desc: [
    { max: 160, message: 'Meta描述不能超过160个字符', trigger: 'blur' }
  ],
  slug: [
    { pattern: /^[a-zA-Z0-9-_]+$/, message: 'Slug只能包含字母、数字、连字符和下划线', trigger: 'blur' }
  ],
  featured_image: [
    { 
      pattern: /^(https?:\/\/.+\.(jpg|jpeg|png|gif|webp)(\?.+)?$|\/uploads\/.+\.(jpg|jpeg|png|gif|webp)(\?.+)?$)/i, 
      message: '请输入有效的图片URL或上传图片', 
      trigger: 'blur' 
    }
  ],
  category_id: [
    { type: 'number', message: '请选择有效的分类', trigger: 'change' }
  ]
};

// 自动保存状态
const autoSaving = ref(false);
/** @type {import('vue').Ref<Date | null>} */
const lastSaveTime = ref(null);
/** @type {import('vue').Ref<ReturnType<typeof setTimeout> | null>} */
const autoSaveInterval = ref(null);
const hasUnsavedChanges = ref(false);
const isRestoringDraft = ref(false); // 标记是否正在恢复草稿
const AUTOSAVE_DELAY = 3000; // 3秒后自动保存
// 工具函数
/** @param {unknown} code @param {string} fallback */
function mapErr(code, fallback) { 
  return ERROR_CODE_MAP.get(Number(code)) || fallback; 
}

// 表单验证调试函数
function debugFormValidation() {
  console.log('=== 表单验证详细信息 ===');
  console.log('标题:', form.value.title, '长度:', form.value.title?.length || 0);
  console.log('内容:', form.value.content_md?.substring(0, 100) + '...', '长度:', form.value.content_md?.length || 0);
  console.log('摘要:', form.value.summary?.substring(0, 50) + '...', '长度:', form.value.summary?.length || 0);
  console.log('标签:', form.value.tags_raw, '长度:', form.value.tags_raw?.length || 0);
  console.log('SEO标题:', form.value.seo_title, '长度:', form.value.seo_title?.length || 0);
  console.log('SEO描述:', form.value.seo_desc, '长度:', form.value.seo_desc?.length || 0);
  console.log('链接:', form.value.slug, '长度:', form.value.slug?.length || 0);
  console.log('封面图:', form.value.featured_image, '长度:', form.value.featured_image?.length || 0);
  
  // 检查编辑器状态
  const editorEl = document.querySelector('.ProseMirror');
  if (editorEl) {
    console.log('编辑器DOM内容长度:', editorEl.textContent?.length || 0);
    console.log('编辑器HTML内容长度:', editorEl.innerHTML?.length || 0);
  }
  console.log('========================');
}

// 格式化保存时间
/** @param {Date | string | null} time */
function formatSaveTime(time) {
  if (!time) return '';
  
  const now = new Date();
  const diff = now.getTime() - new Date(time).getTime();
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  
  const date = new Date(time);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// 图片处理函数
/** @param {{ width?: number, height?: number, url: string }} meta */
function insertImage(meta) {
  const tag = `![${meta.width || ''}x${meta.height || ''}](${meta.url})`;
  form.value.content_md = (form.value.content_md || '') + (form.value.content_md ? '\n' : '') + tag + '\n';
}

/** @param {{ url?: string }} meta */
function onFeaturedCandidate(meta) {
  // 若尚未设置封面图，首次上传默认填入 featured_image
  if (!form.value.featured_image && meta?.url) { 
    form.value.featured_image = meta.url; 
  }
}

/** @param {{ x?: number, y?: number }} f */
function onFocal(f) { 
  form.value.featured_focal_x = f.x ?? form.value.featured_focal_x; 
  form.value.featured_focal_y = f.y ?? form.value.featured_focal_y; 
}

// 加载文章数据用于编辑
/** @param {string} articleId */
async function loadArticleForEdit(articleId) {
  try {
    console.log('正在加载文章数据用于编辑:', articleId);
    loading.value = true;
    
    const response = await API.getArticle(articleId);
    
    if (response.data.code === 0 && response.data.data) {
      const article = response.data.data;
      originalArticle.value = article;
      
      // 检查编辑权限
      if (article.author_id !== userStore.user?.id && !userStore.hasRole(['editor', 'admin'])) {
        message.critical('没有编辑此文章的权限');
        router.push('/');
        return;
      }
      
      // 填充表单数据
      form.value = {
        title: article.title || '',
        content_md: article.content_md || '',
        tags_raw: (article.tags || []).join(', '),
        seo_title: article.seo_title || '',
        seo_desc: article.seo_desc || '',
        slug: article.slug || '',
        summary: article.summary || '',
        featured_image: article.featured_image || '',
        featured_focal_x: article.featured_focal_x || null,
        featured_focal_y: article.featured_focal_y || null,
        enable_schedule: article.status === 'scheduled',
        scheduled_at: article.scheduled_at || '',
        category_id: article.category_id || null
      };
      
      console.log('✅ 文章数据加载完成');
      console.log('📝 文章分类ID:', article.category_id);
      console.log('📝 表单分类ID:', form.value.category_id);
      console.log('📝 可用分类列表:', categories.value);
      
      // 确保CategorySelector组件能接收到正确的值
      await nextTick();
      console.log('📝 NextTick后表单分类ID:', form.value.category_id);
      
      message.success('文章数据加载完成，可以开始编辑');
    } else {
      throw new Error(response.data.message || '加载文章失败');
    }
  } catch (error) {
    console.error('加载文章数据失败:', error);
    const err = /** @type {{ message?: string }} */ (error);
    message.critical('加载文章失败: ' + (err.message || '网络错误'));
    router.push('/');
  } finally {
    loading.value = false;
  }
}

// 表单验证功能
/** @param {string} fieldName @param {unknown} value */
function validateField(fieldName, value) {
  /** @type {Record<string, Array<{ required?: boolean, min?: number, max?: number, message?: string, trigger?: string, pattern?: RegExp, type?: string }>>} */
  const rulesMap = validationRules;
  const rules = rulesMap[fieldName];
  if (!rules) return null;
  
  for (const rule of rules) {
    if (rule.required && (!value || !value.toString().trim())) {
      return rule.message;
    }
    
    if (rule.min && value && value.toString().length < rule.min) {
      return rule.message;
    }
    
    if (rule.max && value && value.toString().length > rule.max) {
      return rule.message;
    }
    
    if (rule.pattern && value && !rule.pattern.test(value.toString())) {
      return rule.message;
    }
  }
  
  return null;
}

function validateForm() {
  /** @type {Record<string, string>} */
  const errors = {};
  let hasErrors = false;
  
  // 验证所有字段
  Object.keys(validationRules).forEach(fieldName => {
    /** @type {Record<string, unknown>} */
    const formData = form.value;
    const value = formData[fieldName];
    const error = validateField(fieldName, value);
    if (error) {
      errors[fieldName] = error;
      hasErrors = true;
    }
  });
  
  // 特殊验证：定时发布
  if (form.value.enable_schedule && !form.value.scheduled_at) {
    errors.scheduled_at = '请选择发布时间';
    hasErrors = true;
  }
  
  if (form.value.enable_schedule && form.value.scheduled_at) {
    const scheduleTime = new Date(form.value.scheduled_at);
    const now = new Date();
    if (scheduleTime <= now) {
      errors.scheduled_at = '发布时间必须大于当前时间';
      hasErrors = true;
    }
  }
  
  formErrors.value = errors;
  return !hasErrors;
}

/** @param {string} fieldName */
function clearFieldError(fieldName) {
  if (formErrors.value[fieldName]) {
    delete formErrors.value[fieldName];
    formErrors.value = { ...formErrors.value };
  }
}

// 实时验证
/** @param {string} fieldName @param {unknown} value */
function handleFieldBlur(fieldName, value) {
  if (showValidation.value) {
    const error = validateField(fieldName, value);
    if (error) {
      formErrors.value[fieldName] = error;
    } else {
      clearFieldError(fieldName);
    }
  }
}

// 提交发布
async function submit() {
  loading.value = true;
  error.value = '';
  success.value = false;
  showValidation.value = true;
  
  try {
    // 优化的内容同步逻辑 - 简化为单一可靠的方法
    console.log('发布前同步编辑器内容...');
    
    const editorRef = blockEditorRef.value;
    if (editorRef && typeof editorRef.syncContent === 'function') {
      try {
        const syncedContent = editorRef.syncContent();
        if (syncedContent && syncedContent.trim()) {
          form.value.content_md = syncedContent;
          console.log('成功同步编辑器内容，长度:', syncedContent.length);
        }
      } catch (editorError) {
        console.error('编辑器内容同步失败:', editorError);
        // 如果同步失败，给用户明确提示
        message.critical('编辑器内容同步失败，请稍后重试');
        loading.value = false;
        return;
      }
    } else if (!editorRef) {
      console.warn('编辑器引用不存在，检查组件是否正确挂载');
    } else {
      console.warn('syncContent方法不存在，编辑器可能未完全初始化');
    }
    
    // 验证内容是否足够
    if (!form.value.content_md || form.value.content_md.trim().length < 10) {
      message.warning('文章内容不能为空，请至少输入10个字符');
      loading.value = false;
      return;
    }
    
    // 内容安全检查和清理
    try {
      console.log('🔍 开始内容安全检查...');
      
      // 检查内容长度
      if (form.value.content_md.length > 500000) { // 500KB限制
        message.critical('文章内容过长，请适当缩减内容长度');
        loading.value = false;
        return;
      }
      
      // 检查是否包含过多的HTML标签
      const htmlTagCount = (form.value.content_md.match(/<[^>]*>/g) || []).length;
      if (htmlTagCount > 1000) {
        console.warn('⚠️ 检测到大量HTML标签:', htmlTagCount);
        message.warning('检测到大量HTML标签，可能影响发布。建议使用Markdown格式编写。');
      }
      
      // 检查是否包含潜在的恶意脚本
      const dangerousPatterns = [
        /<script[^>]*>[\s\S]*?<\/script>/gi,
        /javascript:/gi,
        /on\w+\s*=/gi
      ];
      
      for (const pattern of dangerousPatterns) {
        if (pattern.test(form.value.content_md)) {
          message.critical('内容包含不安全的脚本代码，请移除后重试');
          loading.value = false;
          return;
        }
      }
      
      console.log('✅ 内容安全检查通过');
      
    } catch (validationError) {
      console.error('内容验证失败:', validationError);
      message.critical('内容格式验证失败，请检查内容格式');
      loading.value = false;
      return;
    }
    
    console.log('发布前验证通过，内容长度:', form.value.content_md?.length || 0);
    
    // 简化的表单验证
    if (!validateForm()) {
      const errorFields = Object.keys(formErrors.value);
      const firstErrorMessage = formErrors.value[errorFields[0]];
      
      console.log('表单验证失败:', formErrors.value);
      
      // 显示清晰的错误信息
      message.error({
        message: firstErrorMessage,
        duration: 6000
      });
      
      loading.value = false;
      return;
    }
    
    console.log('表单验证通过，开始发布文章...');
    
    // 构建提交数据
    const tags = form.value.tags_raw.split(',').map(s => s.trim()).filter(Boolean);
    /** @type {Record<string, unknown>} */
    const payload = { 
      title: form.value.title.trim(), 
      content_md: form.value.content_md, 
      tags 
    };
    
    // 编辑文章时，重新进入审核流程
    if (isEditMode.value) {
      payload.status = 'pending';
      console.log('编辑模式：文章状态设置为pending，需要重新审核');
      console.log('📝 提交的payload包含status:', payload.status);
    }
    
    // 可选字段
    if (form.value.slug?.trim()) payload.slug = form.value.slug.trim();
    if (form.value.seo_title?.trim()) payload.seo_title = form.value.seo_title.trim();
    if (form.value.seo_desc?.trim()) payload.seo_desc = form.value.seo_desc.trim();
    if (form.value.summary?.trim()) payload.summary = form.value.summary.trim();
    if (form.value.featured_image?.trim()) payload.featured_image = form.value.featured_image.trim();
    if (form.value.category_id) payload.category_id = form.value.category_id;
    
    // 焦点坐标
    if (form.value.featured_focal_x != null && form.value.featured_focal_y != null) {
      payload.featured_focal_x = form.value.featured_focal_x;
      payload.featured_focal_y = form.value.featured_focal_y;
    }
    
    // 定时发布
    if (form.value.enable_schedule && form.value.scheduled_at) {
      payload.scheduled_at = new Date(form.value.scheduled_at).toISOString();
    }
    
    let resp, data, articleId, slug;
    
    if (isEditMode.value && editingArticleId.value) {
      // 编辑模式：更新现有文章
      console.log('编辑模式：更新文章', editingArticleId.value);
      resp = await API.updateArticle(editingArticleId.value, payload);
      data = resp.data?.data || resp.data;
      articleId = editingArticleId.value;
      slug = data.slug || originalArticle.value?.slug || articleId;
    } else {
      // 创建模式：新建文章
      console.log('创建模式：新建文章');
      resp = await API.ArticlesService.postApiV1Articles(payload);
      data = resp.data?.data || resp.data;
      articleId = data.id;
      slug = data.slug || data.id;
    }
    
    // 提交文章审核
    let publishMessage = '';
    /** @type {'success' | 'warning'} */
    let publishType = 'success';
    
    if (!isEditMode.value) {
      // 新文章需要提交审核
      try {
        await API.submitArticle(articleId);
        console.log('文章已提交审核');
        publishMessage = '恭喜！您的文章已成功发布并提交审核。';
        publishType = 'success';
      } catch (submitError) {
        console.warn('提交审核失败:', submitError);
        publishMessage = '文章已保存为草稿，您可以稍后到文章管理页面提交审核。';
        publishType = 'warning';
      }
    } else {
      // 编辑模式：文章已更新，需要重新审核
      publishMessage = '文章已成功更新！修改后的文章已重新提交审核。';
      publishType = 'warning';
      console.log('文章编辑完成，状态已设置为pending等待审核');
    }
    
    // 清理本地草稿
    if (hasUnsavedChanges.value) {
      hasUnsavedChanges.value = false;
    }
    
    // 调试信息：发布成功
    console.log('文章发布成功，准备跳转...');
    console.log('文章ID:', articleId);
    console.log('文章slug:', slug);
    console.log('跳转路径:', '/article/' + slug);
    
    // 清除loading状态并立即跳转，避免页面重新渲染
    loading.value = false;
    
    // 添加动态样式到页面头部
    const styleId = 'publish-dialog-style';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = `
        .publish-success-dialog.el-message-box {
          position: fixed !important;
          top: 50% !important;
          left: 50% !important;
          transform: translate(-50%, -50%) !important;
          margin: 0 !important;
          z-index: 3000 !important;
          background: #ffffff !important;
          border-radius: 16px !important;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
          border: 1px solid #f1f5f9 !important;
          width: 440px !important;
          max-width: 90vw !important;
          padding: 0 !important;
          overflow: hidden !important;
        }
        .publish-success-dialog.el-message-box .el-message-box__header {
          background: #f1f5f9;
          padding: 32px 24px 16px !important;
          text-align: center !important;
          border-bottom: 1px solid #f0f9ff !important;
        }
        .publish-success-dialog.el-message-box .el-message-box__title {
          font-size: 24px !important;
          font-weight: 700 !important;
          color: #065f46 !important;
        }
        .publish-success-dialog.el-message-box .el-message-box__content {
          padding: 24px 32px !important;
          background: #ffffff !important;
        }
        .publish-success-dialog.el-message-box .el-message-box__message {
          font-size: 16px !important;
          line-height: 1.6 !important;
          color: #374151 !important;
          text-align: center !important;
        }
        .publish-success-dialog.el-message-box .el-message-box__btns {
          padding: 0 32px 32px !important;
          background: #ffffff !important;
          display: flex !important;
          justify-content: center !important;
          gap: 16px !important;
        }
        .publish-success-dialog.el-message-box .dialog-confirm-btn {
          background: #f1f5f9;
          border: none !important;
          border-radius: 12px !important;
          color: #ffffff !important;
          font-weight: 600 !important;
          padding: 14px 28px !important;
          font-size: 15px !important;
          min-width: 120px !important;
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        }
        .publish-success-dialog.el-message-box .dialog-cancel-btn {
          background: #f8fafc !important;
          border: 1px solid #e2e8f0 !important;
          border-radius: 12px !important;
          color: #64748b !important;
          font-weight: 500 !important;
          padding: 14px 28px !important;
          font-size: 15px !important;
          min-width: 120px !important;
        }
      `;
      document.head.appendChild(style);
    }

    // 显示发布成功的弹出对话框
    try {
      const result = await ElMessageBox.confirm(
        `${publishMessage}\n\n是否立即查看您的文章？`,
        isEditMode.value ? '✅ 更新成功！' : (publishType === 'success' ? '🎉 发布成功！' : '📝 保存成功！'),
        {
          confirmButtonText: '查看文章',
          cancelButtonText: isEditMode.value ? '继续编辑' : '稍后查看',
          type: publishType,
          center: true,
          customClass: 'publish-success-dialog',
          distinguishCancelAndClose: true,
          showClose: false,
          closeOnClickModal: false,
          closeOnPressEscape: true,
          showCancelButton: true,
          cancelButtonClass: 'dialog-cancel-btn',
          confirmButtonClass: 'dialog-confirm-btn'
        }
      );
      
      // 用户选择查看文章
      console.log('用户选择查看文章，跳转到:', '/article/' + slug);
      window.location.href = '/article/' + slug;
      
    } catch (action) {
      // 用户选择稍后查看或关闭对话框
      if (action === 'cancel') {
        if (isEditMode.value) {
          console.log('用户选择继续编辑');
          message.info('您可以继续编辑文章');
          // 在编辑模式下，用户选择继续编辑时留在当前页面
        } else {
          console.log('用户选择稍后查看文章');
          message.info('您可以在文章管理页面找到您的文章');
          
          // 跳转到首页
          setTimeout(() => {
            window.location.href = '/'; // 跳转到首页
          }, 1000);
        }
        
      } else {
        console.log('用户关闭了对话框');
        // 用户直接关闭对话框，重置编辑器状态或跳转到安全页面
        message.info('文章已发布成功，您可以在首页查看');
        
        // 为避免组件状态混乱，跳转到首页
        setTimeout(() => {
          window.location.href = '/';
        }, 1500);
      }
    }
    
    return; // 确保成功情况下直接返回
    
  } catch (e) {
    console.error('❌ Submit error:', e);
    const err = /** @type {{ response?: { data?: { message?: string, code?: unknown }, status?: number }, body?: { code?: unknown }, message?: string }} */ (e);
    console.error('❌ Error response:', err.response);
    console.error('❌ Error response data:', err.response?.data);
    console.error('❌ Error status:', err.response?.status);
    console.error('❌ Error message:', err.message);
    
    const code = err.body?.code || err.response?.data?.code;
    const mappedError = mapErr(code, '文章发布失败');
    
    // 详细的错误处理
    if (err.response?.status === 500) {
      error.value = '服务器内部错误，可能是内容格式问题。请检查文章内容是否包含特殊字符或过长的HTML代码。';
      console.error('❌ 500错误详情:', {
        contentLength: form.value.content_md?.length,
        contentPreview: form.value.content_md?.substring(0, 200),
        hasHTML: /<[^>]*>/g.test(form.value.content_md || ''),
        payload: { 
          title: form.value.title?.length,
          content_md_length: form.value.content_md?.length,
          tags: form.value.tags_raw
        }
      });
    } else if (err.response?.data?.message) {
      error.value = err.response.data.message;
    } else {
      error.value = mappedError;
    }
    
    message.error(error.value);
    loading.value = false;
  }
}

// ===== 分类相关函数 =====

// 加载分类列表
async function loadCategories() {
  try {
    categoryLoading.value = true;
    console.log('🔍 开始加载分类列表...');
    console.log('🔒 当前认证状态:', userStore.isAuthenticated);
    console.log('👤 当前用户:', userStore.user);
    
    // 优先使用公开接口，不需要认证
    // 注意：不能使用apiClient，因为它有/api/v1的baseURL，需要直接使用axios
    const response = await axios.get('/public/v1/taxonomy');
    
    console.log('📡 API响应:', response);
    console.log('📡 响应数据:', response.data);
    
    // 处理公开接口API响应格式 {code: 0, message: 'ok', data: {categories: [...], tags: [...]}}
    let categoryData = [];
    if (response.data) {
      if (response.data.code === 0 && response.data.data?.categories) {
        categoryData = response.data.data.categories;
        console.log('✅ 公开接口调用成功，返回分类数据');
      } else if (response.data.code === 0 && response.data.data) {
        // 兼容直接返回数组的情况
        categoryData = Array.isArray(response.data.data) ? response.data.data : [];
        console.log('✅ API调用成功，返回标准格式');
      } else if (Array.isArray(response.data)) {
        categoryData = response.data;
        console.log('📦 收到数组格式数据');
      } else {
        console.warn('⚠️ 意外的响应格式:', response.data);
        console.warn('⚠️ 响应code:', response.data.code);
        console.warn('⚠️ 响应message:', response.data.message);
      }
    }
    
    categories.value = categoryData || [];
    console.log('📁 分类列表加载成功:', categories.value.length, '个分类');
    console.log('📁 分类数据:', categories.value);
    console.log('📁 数据类型检查:', {
      isArray: Array.isArray(categories.value),
      type: typeof categories.value,
      constructor: categories.value.constructor.name
    });
    
    if (categories.value.length === 0) {
      console.warn('⚠️ 分类列表为空，可能需要先在管理后台创建分类');
      message.warning('当前没有可用的分类，请联系管理员创建分类');
    }
    
  } catch (error) {
    const err = /** @type {{ message?: string, response?: { data?: { message?: string }, status?: number }, config?: { url?: string } }} */ (error);
    console.error('❌ 加载分类列表失败:', error);
    console.error('❌ 错误详情:', {
      message: err.message,
      response: err.response?.data,
      status: err.response?.status,
      url: err.config?.url
    });
    
    // 如果公开接口失败，尝试使用认证接口
    console.log('🔄 公开接口失败，尝试使用认证接口...');
    try {
      const authResponse = await API.getRootCategories();
      console.log('📡 认证接口响应:', authResponse.data);
      
      if (authResponse.data.code === 0 && authResponse.data.data) {
        categories.value = Array.isArray(authResponse.data.data) ? authResponse.data.data : [];
        console.log('✅ 认证接口成功，加载了', categories.value.length, '个分类');
        console.log('📁 认证接口数据类型检查:', {
          isArray: Array.isArray(categories.value),
          type: typeof categories.value,
          constructor: categories.value.constructor?.name
        });
        return; // 成功获取数据，直接返回
      }
    } catch (authError) {
      console.error('❌ 认证接口也失败了:', authError);
    }
    
    message.critical(`加载分类列表失败: ${err.response?.data?.message || err.message || '网络错误'}`);
    categories.value = [];
    
    // 最后的降级方案
    console.log('🔄 尝试最后的降级方案...');
    try {
      // 尝试使用生成的API适配器
      const fallbackResponse = await API.TaxonomyService.listCategories();
      const fallbackData = fallbackResponse.data || [];
      categories.value = Array.isArray(fallbackData) ? fallbackData : [];
      console.log('✅ 降级方案成功，加载了', categories.value.length, '个分类');
      console.log('📁 降级方案数据类型检查:', {
        isArray: Array.isArray(categories.value),
        type: typeof categories.value,
        constructor: categories.value.constructor?.name
      });
    } catch (fallbackError) {
      console.error('❌ 降级方案也失败了:', fallbackError);
    }
  } finally {
    categoryLoading.value = false;
  }
}

// 处理分类选择变化
/** @param {number} categoryId */
function handleCategoryChange(categoryId) {
  form.value.category_id = categoryId;
  clearFieldError('category_id');
  
  if (categoryId) {
    const selectedCategory = categories.value.find(cat => cat.id === categoryId);
    if (selectedCategory) {
      console.log('🏷️ 已选择分类:', selectedCategory.name);
      
      // 触发自动保存（如果有其他内容）
      if (form.value.title || form.value.content_md) {
        triggerAutoSave();
      }
    }
  }
}

// 加载可用标签
async function loadAvailableTags() {
  try {
    tagsLoading.value = true;
    const response = await API.getTaxonomyStats();
    
    if (response.data.code === 0) {
      availableTags.value = response.data.data.tags || [];
      console.log('✅ 标签加载成功，共', availableTags.value.length, '个标签');
    } else {
      console.error('❌ 标签加载失败:', response.data.message);
      message.warning('标签加载失败，但不影响文章创建');
    }
  } catch (error) {
    console.error('❌ 标签加载出错:', error);
    message.warning('标签加载失败，但不影响文章创建');
  } finally {
    tagsLoading.value = false;
  }
}

// 更新tags_raw字段
/** @param {string[]} tags */
function updateTagsRaw(tags) {
  selectedTags.value = tags;
  form.value.tags_raw = tags.join(', ');
  console.log('🏷️ 标签已更新:', tags);
  
  // 触发自动保存
  if (form.value.title || form.value.content_md) {
    triggerAutoSave();
  }
}

// 初始化已选标签（从tags_raw恢复）
function initSelectedTags() {
  if (form.value.tags_raw) {
    selectedTags.value = form.value.tags_raw
      .split(',')
      .map(tag => tag.trim())
      .filter(Boolean);
  }
}

// 处理AI推荐选择
/**
 * @param {{ category: { id: number, name: string }, confidence?: number, reason?: string }} recommendation
 */
function handleRecommendationSelected(recommendation) {
  console.log('🤖 AI推荐分类被选择:', recommendation);
  
  // 统计推荐效果（可用于优化AI模型）
  const analyticsData = {
    action: 'ai_category_recommendation_selected',
    categoryId: recommendation.category.id,
    categoryName: recommendation.category.name,
    confidence: recommendation.confidence,
    reason: recommendation.reason,
    articleData: {
      titleLength: form.value.title?.length || 0,
      contentLength: form.value.content_md?.length || 0,
      hasTitle: !!form.value.title,
      hasContent: !!form.value.content_md,
      hasSummary: !!form.value.summary,
      tagCount: form.value.tags_raw ? form.value.tags_raw.split(',').length : 0
    }
  };
  
  // 这里可以发送统计数据到后端用于模型优化
  console.log('📊 AI推荐统计数据:', analyticsData);
  
  message.success(`已选择AI推荐的分类：${recommendation.category.name}`);
}

// 保存草稿
async function saveDraft() {
  try {
    autoSaving.value = true;
    
    // 检查必要字段
    if (!form.value.title?.trim() && !form.value.content_md?.trim()) {
      message.warning('请至少填写标题或内容后再保存草稿');
      return;
    }
    
    // 构建草稿数据
    /** @type {Record<string, unknown>} */
    const draftData = {
      title: form.value.title?.trim() || '未命名草稿',
      content_md: form.value.content_md || '',
      summary: form.value.summary?.trim() || '',
      featured_image: form.value.featured_image?.trim() || '',
      tags_raw: form.value.tags_raw?.trim() || '',
      seo_title: form.value.seo_title?.trim() || '',
      seo_desc: form.value.seo_desc?.trim() || '',
      slug: form.value.slug?.trim() || '',
      status: 'draft' // 标记为草稿状态
    };
    
    // 焦点坐标
    if (form.value.featured_focal_x != null && form.value.featured_focal_y != null) {
      draftData.featured_focal_x = form.value.featured_focal_x;
      draftData.featured_focal_y = form.value.featured_focal_y;
    }
    
    // 保存到本地存储
    const draftKey = 'article_draft_' + Date.now();
    localStorage.setItem(draftKey, JSON.stringify({
      ...draftData,
      savedAt: new Date().toISOString(),
      id: draftKey
    }));
    
    // 清理旧草稿（保留最近5个）
    cleanupOldDrafts();
    
    lastSaveTime.value = new Date();
    hasUnsavedChanges.value = false;
    
    message.success('💾 草稿已保存到本地');
    
  } catch (e) {
    console.error('Draft save error:', e);
    message.critical('草稿保存失败');
  } finally {
    autoSaving.value = false;
  }
}

// 清理旧草稿
function cleanupOldDrafts() {
  try {
    const draftKeys = Object.keys(localStorage).filter(key => key.startsWith('article_draft_'));
    if (draftKeys.length > 5) {
      // 按时间排序，删除最旧的
      const draftsWithTime = draftKeys.map(key => {
        const draft = JSON.parse(localStorage.getItem(key) || '{}');
        return { key, savedAt: draft.savedAt || '1970-01-01' };
      }).sort((a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime());
      
      // 删除超过5个的旧草稿
      draftsWithTime.slice(5).forEach(draft => {
        localStorage.removeItem(draft.key);
      });
    }
  } catch (e) {
    console.error('Cleanup drafts error:', e);
  }
}

// 自动保存功能
function triggerAutoSave() {
  // 如果正在恢复草稿，忽略触发
  if (isRestoringDraft.value) {
    console.log('正在恢复草稿，跳过自动保存触发');
    return;
  }
  
  // 清除之前的定时器
  if (autoSaveInterval.value) {
    clearTimeout(autoSaveInterval.value);
  }
  
  // 标记有未保存的更改
  hasUnsavedChanges.value = true;
  
  // 设置新的定时器
  autoSaveInterval.value = setTimeout(() => {
    if (hasUnsavedChanges.value && !isRestoringDraft.value) {
      saveDraft();
    }
  }, AUTOSAVE_DELAY);
}

// 恢复草稿
async function loadLatestDraft() {
  try {
    const draftKeys = Object.keys(localStorage).filter(key => key.startsWith('article_draft_'));
    if (draftKeys.length === 0) return;
    
    // 找到最新的草稿
    const latestDraftKey = draftKeys.reduce((latest, key) => {
      const current = JSON.parse(localStorage.getItem(key) || '{}');
      const latestData = JSON.parse(localStorage.getItem(latest) || '{}');
      return new Date(current.savedAt || 0) > new Date(latestData.savedAt || 0) ? key : latest;
    });
    
    const draftData = JSON.parse(localStorage.getItem(latestDraftKey) || '{}');
    const saveTime = new Date(draftData.savedAt);
    const now = new Date();
    const hoursDiff = (now.getTime() - saveTime.getTime()) / (1000 * 60 * 60);
    
    // 如果草稿是24小时内的，显示统一的卡片对话框询问是否恢复
    if (hoursDiff < 24) {
      // 添加草稿对话框样式
      const styleId = 'draft-dialog-style';
      if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
          .draft-restore-dialog.el-message-box {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            margin: 0 !important;
            z-index: 3000 !important;
            background: #ffffff !important;
            border-radius: 16px !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
            border: 1px solid #f1f5f9 !important;
            width: 440px !important;
            max-width: 90vw !important;
            padding: 0 !important;
            overflow: hidden !important;
          }
          .draft-restore-dialog.el-message-box .el-message-box__header {
            background: #f1f5f9;
            padding: 32px 24px 16px !important;
            text-align: center !important;
            border-bottom: 1px solid #e5e7eb !important;
          }
          .draft-restore-dialog.el-message-box .el-message-box__title {
            font-size: 24px !important;
            font-weight: 700 !important;
            color: #1f2937 !important;
          }
          .draft-restore-dialog.el-message-box .el-message-box__content {
            padding: 24px 32px !important;
            background: #ffffff !important;
          }
          .draft-restore-dialog.el-message-box .el-message-box__message {
            font-size: 16px !important;
            line-height: 1.6 !important;
            color: #374151 !important;
            text-align: left !important;
            white-space: pre-line !important;
          }
          .draft-restore-dialog.el-message-box .el-message-box__btns {
            padding: 0 32px 32px !important;
            background: #ffffff !important;
            display: flex !important;
            justify-content: center !important;
            gap: 16px !important;
          }
          .draft-restore-dialog.el-message-box .dialog-restore-btn {
            background: #f1f5f9;
            border: none !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            padding: 14px 28px !important;
            font-size: 15px !important;
            min-width: 120px !important;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
          }
          .draft-restore-dialog.el-message-box .dialog-skip-btn {
            background: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px !important;
            color: #64748b !important;
            font-weight: 500 !important;
            padding: 14px 28px !important;
            font-size: 15px !important;
            min-width: 120px !important;
          }
        `;
        document.head.appendChild(style);
      }
      
      try {
        const result = await ElMessageBox.confirm(
          `发现 ${Math.floor(hoursDiff)} 小时前的草稿\n\n标题：${draftData.title || '未命名草稿'}\n内容：${(draftData.content_md || '').substring(0, 100)}${(draftData.content_md || '').length > 100 ? '...' : ''}\n\n是否恢复这个草稿继续编辑？`,
          '📝 发现草稿',
          {
            confirmButtonText: '恢复草稿',
            cancelButtonText: '跳过',
            type: 'info',
            center: true,
            customClass: 'draft-restore-dialog',
            distinguishCancelAndClose: true,
            showClose: false,
            closeOnClickModal: false,
            closeOnPressEscape: true,
            showCancelButton: true,
            cancelButtonClass: 'dialog-skip-btn',
            confirmButtonClass: 'dialog-restore-btn'
          }
        );
        
        // 用户选择恢复草稿 - 采用更安全的同步方式
        console.log('用户选择恢复草稿');
        
        try {
          // 立即设置恢复标志
          isRestoringDraft.value = true;
          hasUnsavedChanges.value = false;
          
          // 清除任何自动保存定时器
          if (autoSaveInterval.value) {
            clearTimeout(autoSaveInterval.value);
            autoSaveInterval.value = null;
          }
          
          // 同步恢复基础表单数据（不包含content_md，避免触发编辑器更新）
          Object.keys(draftData).forEach(key => {
            /** @type {Record<string, unknown>} */
            const formData = form.value;
            if (key !== 'savedAt' && key !== 'id' && key !== 'status' && 
                key !== 'content_md' && formData.hasOwnProperty(key)) {
              formData[key] = draftData[key];
            }
          });
          
          // 单独处理content_md，使用更安全的方式
          await nextTick();
          
          // 使用Vue的批量更新机制，避免响应式冲突
          await nextTick(() => {
            // 在下一个微任务中安全地更新content_md
            form.value.content_md = draftData.content_md || '';
          });
          
          // 等待两个渲染周期确保状态完全稳定
          await nextTick();
          await nextTick();
          
          // 将编辑器内容设置延迟到宏任务队列，完全避开Vue的更新周期
          setTimeout(async () => {
            try {
              // 再次确认编辑器引用存在且有效
              if (blockEditorRef.value && 
                  typeof blockEditorRef.value.setContent === 'function') {
                
                // 在设置内容前再等待一个tick，确保DOM完全稳定
                await nextTick();
                
                blockEditorRef.value.setContent(draftData.content_md || '');
                console.log('编辑器内容同步成功');
              } else {
                console.warn('编辑器引用无效或组件已卸载，跳过内容设置');
              }
            } catch (e) {
              console.warn('设置编辑器内容失败:', e);
              // 不影响整个恢复流程
            }
          }, 100);
          
          // 最终状态重置 - 使用更长延迟确保编辑器稳定
          setTimeout(() => {
            isRestoringDraft.value = false;
            hasUnsavedChanges.value = false;
            console.log('草稿恢复完成，导航已解锁');
            console.log('最终状态 - hasUnsavedChanges:', hasUnsavedChanges.value);
            console.log('最终状态 - isRestoringDraft:', isRestoringDraft.value);
            
            // 草稿恢复完成，编辑器状态稳定
            
            // 显示成功消息，并提示用户现在可以安全导航
            console.log("📝 草稿恢复完成，用户可以安全导航");
            message.success('📝 草稿已恢复！现在可以安全导航到其他页面。');
          }, 1000);
          
        } catch (error) {
          const err = /** @type {{ message?: string }} */ (error);
          console.error('草稿恢复过程中出现错误:', error);
          
          // 检查是否是Vue响应式系统的错误（这种情况下数据可能已经恢复成功）
          const isVueRenderError = err.message && err.message.includes('__vnode');
          
          if (isVueRenderError) {
            console.warn('检测到Vue渲染错误，但数据可能已成功恢复');
            // 延迟检查恢复状态，避免立即显示错误
            setTimeout(() => {
              // 检查草稿数据是否已实际恢复
              const hasContent = form.value.title || form.value.content_md;
              if (hasContent) {
                console.log('数据已成功恢复，忽略Vue渲染错误');
                // 正常完成恢复流程
                isRestoringDraft.value = false;
                hasUnsavedChanges.value = false;
                message.success({
                  message: '📝 草稿已恢复！',
                  duration: 3000
                });
              } else {
                // 真正的恢复失败
                isRestoringDraft.value = false;
                hasUnsavedChanges.value = false;
                message.critical('草稿恢复失败，请重试');
              }
            }, 500);
          } else {
            // 其他类型的错误
            isRestoringDraft.value = false;
            hasUnsavedChanges.value = false;
            console.log("草稿恢复失败，请重试");
            message.critical('草稿恢复失败，请重试');
          }
        }
        
      } catch (action) {
        // 用户选择跳过或关闭
        if (action === 'cancel') {
          console.log('用户选择跳过草稿恢复');
        } else {
          console.log('用户关闭了草稿对话框');
        }
        // 不显示任何额外的通知，保持安静
      }
    }
  } catch (e) {
    console.error('Load draft error:', e);
    // 确保状态重置，避免用户界面卡住
    if (isRestoringDraft.value) {
      isRestoringDraft.value = false;
      hasUnsavedChanges.value = false;
      console.log('全局错误处理：重置草稿恢复状态');
    }
  }
}

// 监听页面离开事件
/** @param {BeforeUnloadEvent} e */
function handleBeforeUnload(e) {
  // 如果正在恢复草稿，不阻止导航
  if (isRestoringDraft.value) {
    console.log('正在恢复草稿，允许页面导航');
    return;
  }
  
  if (hasUnsavedChanges.value) {
    console.log('检测到未保存更改，阻止页面离开');
    e.preventDefault();
    e.returnValue = '您有未保存的更改，确定要离开页面吗？';
    return '您有未保存的更改，确定要离开页面吗？';
  } else {
    console.log('没有未保存更改，允许页面导航');
  }
}

// 键盘快捷键支持
/** @param {KeyboardEvent} e */
function handleKeyDown(e) {
  // Ctrl/Cmd 组合键
  const isCtrlOrCmd = e.ctrlKey || e.metaKey;
  
  if (isCtrlOrCmd) {
    switch (e.key.toLowerCase()) {
      case 's':
        // Ctrl+S: 保存草稿
        e.preventDefault();
        saveDraft();
        break;
        
      case 'enter':
        // Ctrl+Enter: 发布文章
        e.preventDefault();
        if (!loading.value) {
          submit();
        }
        break;
        
      case 'k':
        // Ctrl+K: 显示快捷键帮助
        e.preventDefault();
        showKeyboardShortcuts();
        break;
        
      case 'i':
        // Ctrl+I: 插入图片
        if (e.shiftKey) {
          e.preventDefault();
          // 触发图片上传
          /** @type {HTMLElement | null} */
          const uploadInput = document.querySelector('.cover-uploader input[type="file"]');
          if (uploadInput) {
            uploadInput.click();
          }
        }
        break;
        
      case 'l':
        // Ctrl+L: 插入链接  
        if (e.shiftKey) {
          e.preventDefault();
          // 聚焦到编辑器区域
          /** @type {HTMLElement | null} */
          const editorElement = document.querySelector('.editor-content');
          if (editorElement) {
            editorElement.focus();
            message.info('已聚焦到编辑器，请使用编辑器工具栏插入链接');
          }
        }
        break;
        
      case '/':
        // Ctrl+/: 切换预览模式
        e.preventDefault();
        message.info('预览功能将在后续版本中实现');
        break;
    }
  }
  
  // 其他快捷键
  switch (e.key) {
    case 'Escape':
      // ESC: 清除错误信息
      if (error.value) {
        error.value = '';
      }
      break;
      
    case 'F1':
      // F1: 显示帮助
      e.preventDefault();
      showKeyboardShortcuts();
      break;
  }
}

// 显示快捷键帮助
function showKeyboardShortcuts() {
  const shortcuts = [
    { key: 'Ctrl+S', desc: '保存草稿到本地' },
    { key: 'Ctrl+Enter', desc: '发布文章' },
    { key: 'Ctrl+Shift+I', desc: '上传封面图片' },
    { key: 'Ctrl+Shift+L', desc: '在编辑器中插入链接' },
    { key: 'Ctrl+K / F1', desc: '显示此帮助' },
    { key: 'Escape', desc: '清除错误信息' }
  ];
  
  const shortcutText = shortcuts.map(s => `${s.key}: ${s.desc}`).join('\n');
  
  ElMessage({
    message: `键盘快捷键:\n\n${shortcutText}`,
    type: 'info',
    duration: 0,
    showClose: true,
    dangerouslyUseHTMLString: false,
    customClass: 'keyboard-shortcuts-message'
  });
}

// 监听表单变化以触发自动保存
watch(() => [form.value.title, form.value.content_md, form.value.summary, form.value.tags_raw], () => {
  triggerAutoSave();
}, { deep: true });

// 监听tags_raw变化，同步到selectedTags
watch(() => form.value.tags_raw, (newValue) => {
  if (newValue !== selectedTags.value.join(', ')) {
    initSelectedTags();
  }
}, { immediate: true });

// 监听内容编辑器变化以验证
watch(() => form.value.content_md, (newValue) => {
  if (showValidation.value) {
    handleFieldBlur('content_md', newValue);
  }
});

// 生命周期钩子
onMounted(async () => {
  // 添加Promise错误处理，专门处理__vnode相关错误
  /** @param {PromiseRejectionEvent} event */
  const handleUnhandledRejection = (event) => {
    if (event.reason && event.reason.message && event.reason.message.includes('__vnode')) {
      console.warn('检测到Vue虚拟节点Promise错误，已静默处理:', event.reason.message);
      // 注意：不调用preventDefault()，避免干扰其他Promise链和路由导航
      // 只记录日志，让Vue内部处理这些错误
    }
  };
  
  // 保存到window对象以便清理时使用
  window.vueErrorHandler = handleUnhandledRejection;
  window.addEventListener('unhandledrejection', handleUnhandledRejection);
  
  // 先加载分类列表和标签，确保数据可用
  await loadCategories();
  await loadAvailableTags();
  
  // 检查是否为编辑模式
  const articleIdParam = route.params.id;
  const articleId = Array.isArray(articleIdParam) ? articleIdParam[0] : (articleIdParam || '');
  if (articleId && route.meta.editMode) {
    isEditMode.value = true;
    editingArticleId.value = parseInt(articleId, 10) || null;
    setMeta({ title: '编辑文章', description: '编辑现有文章内容' });
    
    // 在分类数据加载完成后再加载文章数据
    await loadArticleForEdit(articleId);
  } else {
    setMeta({ title: '撰写新文章', description: '创作中心 - 新建文章' });
  }
  
  // 认证状态检查
  console.log('📝 NewArticle组件挂载，检查认证状态');
  console.log('📝 当前认证状态:', userStore.isAuthenticated);
  console.log('📝 当前用户:', userStore.user);
  console.log('📝 当前token:', userStore.token ? '已存在' : '不存在');
  console.log('📝 localStorage token:', localStorage.getItem('access_token') ? '已存在' : '不存在');
  
  // 如果未认证，尝试初始化认证状态
  if (!userStore.isAuthenticated) {
    console.log('📝 用户未认证，尝试初始化认证状态...');
    await userStore.initAuth();
    console.log('📝 认证初始化完成，当前状态:', userStore.isAuthenticated);
    
    // 如果仍未认证，重定向到登录页
    if (!userStore.isAuthenticated) {
      console.log('📝 用户仍未认证，重定向到登录页');
      message.warning('请先登录后再创建文章');
      router.push('/login');
      return;
    }
  }
  
  // 页面加载后检查是否有草稿 - 只在新建文章时显示
  if (!isEditMode.value) {
    setTimeout(() => {
      nextTick(() => {
        loadLatestDraft().catch(error => {
          console.error('草稿恢复异步错误:', error);
          // 确保状态重置
          if (isRestoringDraft.value) {
            isRestoringDraft.value = false;
            hasUnsavedChanges.value = false;
          }
        });
      });
    }, 300);
  }
  
  // 监听页面离开事件
  window.addEventListener('beforeunload', handleBeforeUnload);
  
  // 添加键盘事件监听
  document.addEventListener('keydown', handleKeyDown);
  
  // 组件初始化完成
  console.log('📝 NewArticle组件初始化完成');
});

onBeforeUnmount(() => {
  // 清理定时器
  if (autoSaveInterval.value) {
    clearTimeout(autoSaveInterval.value);
  }
  
  // 移除事件监听
  window.removeEventListener('beforeunload', handleBeforeUnload);
  document.removeEventListener('keydown', handleKeyDown);
  
  // 移除Promise错误处理（如果存在）
  if (window.vueErrorHandler) {
    window.removeEventListener('unhandledrejection', window.vueErrorHandler);
    delete window.vueErrorHandler;
  }
  
  // 如果有未保存的更改，自动保存一次
  if (hasUnsavedChanges.value) {
    saveDraft();
  }
});

// 路由离开守卫 - 处理未保存的更改
onBeforeRouteLeave((to, from, next) => {
  console.log('🚦 路由守卫检查 - hasUnsavedChanges:', hasUnsavedChanges.value);
  console.log('🚦 路由守卫检查 - isRestoringDraft:', isRestoringDraft.value);
  console.log('🚦 路由守卫检查 - 目标路径:', to.path);
  console.log('🚦 路由守卫检查 - 表单内容:', {
    title: form.value.title?.length || 0,
    content: form.value.content_md?.length || 0
  });
  
  // 如果正在恢复草稿或已完成恢复，直接允许导航
  if (isRestoringDraft.value) {
    console.log('🚦 正在恢复草稿，允许导航');
    next();
    return;
  }
  
  // 特殊处理：如果导航到主页且表单基本为空，直接允许
  if (to.path === '/' && (!form.value.title?.trim() && (!form.value.content_md?.trim() || form.value.content_md.length < 10))) {
    console.log('🚦 导航到主页且内容基本为空，强制允许导航');
    hasUnsavedChanges.value = false;
    next();
    return;
  }
  
  // 检查未保存更改（但给一个宽松的判断）
  if (hasUnsavedChanges.value) {
    console.log('🚦 检测到未保存更改，询问用户');
    try {
      const answer = window.confirm('您有未保存的更改，确定要离开页面吗？');
      next(answer);
    } catch (e) {
      console.error('确认对话框出错，默认允许导航:', e);
      next();
    }
  } else {
    console.log('🚦 无未保存更改，允许导航');
    next();
  }
});

// 测试多消息场景处理效果的方法
function testBatchMessageHandling() {
  console.log('🧪 开始测试批量消息处理');
  
  // 模拟编辑器初始化时的多个消息
  message.info('编辑器初始化中...');
  message.success('草稿数据加载完成');  
  message.warning('未找到匹配的分类');
  message.critical('网络连接失败');
  message.info('自动保存已开启');
  message.warning('检测到大量HTML标签');
  message.success('分类加载成功');
  
  console.log('🧪 已触发7条不同优先级的消息，查看效果');
}

// 在开发模式下暴露测试方法到全局
if (process.env.NODE_ENV === 'development') {
  window.testBatchMessages = testBatchMessageHandling;
}
</script>
<style scoped>
/* 编辑器完整版(05 §24 Main/Side + §25 三键发布;公开站 token) */
.editor-page {
  padding: 38px 0 60px;
}
.editor-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  flex-wrap: wrap;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.page-title {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.04em;
  color: var(--text);
}
.page-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--muted);
}
.head-keys {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.key-btn {
  height: 36px;
  padding: 0 16px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 180ms ease, border-color 180ms ease, opacity 180ms ease;
}
.key-btn.ghost {
  border: 1px solid var(--line-strong);
  background: var(--surface);
  color: var(--text);
}
.key-btn.ghost:hover:not(:disabled) {
  border-color: var(--text);
}
.key-btn.primary {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
  font-weight: 650;
}
.key-btn.primary:hover:not(:disabled) {
  background: #1d4ed8;
  border-color: #1d4ed8;
}
.key-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.editor-alert {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.6;
}
.editor-alert.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}
.editor-alert.warn {
  background: var(--signal-soft, #fff0ea);
  border: 1px solid #fed7aa;
  color: var(--signal-ink, #a53b21);
}
.autosave-strip {
  margin-top: 12px;
  padding: 8px 14px;
  border: 1px dashed var(--line);
  border-radius: 10px;
  font-size: 12px;
  color: var(--muted);
}

.editor-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 26px;
  align-items: start;
  padding-top: 26px;
}

/* Main 列:标题 / 摘要 / 封面 / 正文 */
.editor-main .block {
  padding: 0 0 26px;
  margin: 0 0 26px;
  border-bottom: 1px solid var(--line);
}
.editor-main .block:last-child {
  border-bottom: 0;
  margin-bottom: 0;
  padding-bottom: 0;
}
.field-label {
  display: block;
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 650;
  color: var(--text);
}
.req {
  color: #dc2626;
  font-style: normal;
}
.title-input {
  width: 100%;
  padding: 10px 2px;
  border: 0;
  border-bottom: 2px solid var(--line);
  background: transparent;
  color: var(--text);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  outline: none;
  border-radius: 0;
}
.title-input:focus {
  border-bottom-color: var(--text);
}
.title-input::placeholder {
  color: var(--muted);
  opacity: 0.6;
  font-weight: 500;
}
.summary-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  line-height: 1.7;
  resize: vertical;
  outline: none;
  font-family: inherit;
}
.summary-input:focus {
  border-color: var(--line-strong);
}
.summary-input::placeholder {
  color: var(--muted);
  opacity: 0.6;
}
.field-count {
  margin-top: 6px;
  text-align: right;
  font-size: 11px;
  color: var(--muted);
}
.field-error {
  margin: 6px 0 0;
  font-size: 12px;
  color: #dc2626;
}
.hint {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--muted);
}
.error-input,
.error-input:focus {
  border-color: #dc2626 !important;
}

.kbd-hint {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 12px;
  padding: 8px 12px;
  border-top: 1px solid var(--line);
  border-radius: 0 0 10px 10px;
  background: var(--surface-2);
}
.kbd-btn {
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}
.kbd-btn:hover {
  color: var(--text);
  text-decoration: underline;
}
.kbd-preview {
  font-size: 11px;
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

/* Side 列:状态 / 分类 / 标签 / 链接 / SEO / 定时 */
.editor-side {
  position: sticky;
  top: 88px;
  display: grid;
  gap: 14px;
}
.side-block {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
  padding: 14px 16px 16px;
}
.side-block h2 {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 650;
  color: var(--text);
}
.side-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  outline: none;
}
.side-input:focus {
  border-color: var(--line-strong);
}
.side-category {
  width: 100%;
}
.status-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 0;
  border-top: 1px solid var(--line);
  font-size: 12px;
}
.status-row:first-of-type {
  border-top: 0;
  padding-top: 2px;
}
.status-label {
  color: var(--muted);
}
.status-value {
  color: var(--text);
  font-weight: 600;
  text-align: right;
}

@media (max-width: 1100px) {
  .editor-grid {
    grid-template-columns: 1fr;
  }
  .editor-side {
    position: static;
  }
  .preview-h1 {
    font-size: 30px;
  }
}
@media (max-width: 640px) {
  .editor-page {
    padding-top: 24px;
  }
  .editor-top {
    flex-direction: column;
    align-items: stretch;
  }
  .key-btn {
    flex: 1;
  }
  .preview-canvas {
    padding: 28px 18px 60px;
  }
}
</style>

<!-- 全局样式确保对话框样式生效 -->
<style>
/* 发布成功对话框全局样式 */
.publish-success-dialog.el-message-box {
  background: #ffffff !important;
  border-radius: 16px !important;
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
  border: 1px solid #f1f5f9 !important;
  position: fixed !important;
  top: 50% !important;
  left: 50% !important;
  transform: translate(-50%, -50%) !important;
  margin: 0 !important;
  z-index: 3000 !important;
  width: 440px !important;
  max-width: 90vw !important;
  padding: 0 !important;
  overflow: hidden !important;
}

.publish-success-dialog.el-message-box .el-message-box__close {
  position: absolute !important;
  top: 16px !important;
  right: 16px !important;
  width: 32px !important;
  height: 32px !important;
  background: rgba(0, 0, 0, 0.06) !important;
  border-radius: 50% !important;
  color: #6b7280 !important;
  font-size: 16px !important;
  line-height: 32px !important;
  text-align: center !important;
  transition: all 0.2s ease !important;
  cursor: pointer !important;
}

.publish-success-dialog.el-message-box .el-message-box__close:hover {
  background: rgba(0, 0, 0, 0.12) !important;
  color: #374151 !important;
}

.publish-success-dialog.el-message-box .el-message-box__header {
  background: var(--bg, #f7f7f5);
  padding: 32px 24px 16px !important;
  text-align: center !important;
  border-bottom: 1px solid var(--line, #e3e3df) !important;
  position: relative !important;
}

.publish-success-dialog.el-message-box .el-message-box__title {
  font-size: 20px !important;
  font-weight: 700 !important;
  color: var(--text, #171717) !important;
  line-height: 1.3 !important;
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
}

.publish-success-dialog.el-message-box .el-message-box__content {
  padding: 24px 32px !important;
  background: #ffffff !important;
}

.publish-success-dialog.el-message-box .el-message-box__message {
  font-size: 16px !important;
  line-height: 1.6 !important;
  color: #374151 !important;
  text-align: center !important;
  white-space: pre-line !important;
  margin: 0 !important;
}

.publish-success-dialog.el-message-box .el-message-box__btns {
  padding: 0 32px 32px !important;
  background: #ffffff !important;
  display: flex !important;
  justify-content: center !important;
  gap: 16px !important;
}

.publish-success-dialog.el-message-box .dialog-confirm-btn {
  background: #2563eb !important;
  border: none !important;
  border-radius: 10px !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  padding: 14px 28px !important;
  font-size: 15px !important;
  min-width: 120px !important;
  height: auto !important;
  transition: background-color 0.2s ease !important;
}

.publish-success-dialog.el-message-box .dialog-confirm-btn:hover {
  background: #1d4ed8 !important;
}

.publish-success-dialog.el-message-box .dialog-cancel-btn {
  background: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  color: #64748b !important;
  font-weight: 500 !important;
  padding: 14px 28px !important;
  font-size: 15px !important;
  min-width: 120px !important;
  height: auto !important;
  transition: all 0.2s ease !important;
}

.publish-success-dialog.el-message-box .dialog-cancel-btn:hover {
  background: #f1f5f9 !important;
  border-color: #cbd5e1 !important;
  color: #475569 !important;
  transform: translateY(-1px) !important;
}

@media (max-width: 768px) {
  .publish-success-dialog.el-message-box {
    width: 90% !important;
    max-width: 380px !important;
  }
  
  .publish-success-dialog.el-message-box .el-message-box__header {
    padding: 24px 20px 12px !important;
  }
  
  .publish-success-dialog.el-message-box .el-message-box__title {
    font-size: 20px !important;
  }
  
  .publish-success-dialog.el-message-box .el-message-box__content {
    padding: 20px 24px !important;
  }
  
  .publish-success-dialog.el-message-box .el-message-box__message {
    font-size: 15px !important;
  }
  
  .publish-success-dialog.el-message-box .el-message-box__btns {
    padding: 0 24px 24px !important;
    flex-direction: column !important;
    gap: 12px !important;
  }
  
  .publish-success-dialog.el-message-box .dialog-confirm-btn,
  .publish-success-dialog.el-message-box .dialog-cancel-btn {
    width: 100% !important;
    padding: 12px 24px !important;
    font-size: 14px !important;
  }
  
  .publish-success-dialog.el-message-box .el-message-box__close {
    top: 12px !important;
    right: 12px !important;
    width: 28px !important;
    height: 28px !important;
    line-height: 28px !important;
    font-size: 14px !important;
  }
}
/* 预览正文排版(纯 DOM 节点,需全局样式) */
.preview-body { font-size: 16px; line-height: 1.85; color: var(--text); word-break: break-word; }
.preview-body h1, .preview-body h2, .preview-body h3, .preview-body h4 { margin: 1.6em 0 0.6em; line-height: 1.35; letter-spacing: -0.02em; }
.preview-body h1 { font-size: 28px; }
.preview-body h2 { font-size: 24px; }
.preview-body h3 { font-size: 20px; }
.preview-body h4 { font-size: 17px; }
.preview-body p { margin: 0 0 1.1em; }
.preview-body a { color: #2563eb; }
.preview-body ul, .preview-body ol { margin: 0 0 1.1em; padding-left: 1.6em; }
.preview-body li { margin: 0.3em 0; }
.preview-body blockquote { margin: 1.2em 0; padding: 8px 18px; border-left: 3px solid var(--line-strong); color: var(--muted); }
.preview-body code { padding: 2px 6px; border-radius: 6px; background: var(--surface-2); font-size: 0.88em; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.preview-body pre { margin: 1.2em 0; padding: 16px; border-radius: 12px; background: var(--code, #151614); overflow-x: auto; }
.preview-body pre code { padding: 0; background: transparent; color: var(--code-text, #e9e9e2); font-size: 13px; line-height: 1.7; }
.preview-body img { max-width: 100%; border-radius: 10px; }
.preview-body table { width: 100%; border-collapse: collapse; margin: 1.2em 0; font-size: 14px; }
.preview-body th, .preview-body td { border: 1px solid var(--line); padding: 8px 12px; text-align: left; }
.preview-body hr { border: 0; border-top: 1px solid var(--line); margin: 2em 0; }
</style>
