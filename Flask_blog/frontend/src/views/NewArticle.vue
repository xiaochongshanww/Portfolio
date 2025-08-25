<template>
  <div class="article-editor-container">
    <!-- 页面头部 -->
    <div class="editor-header">
      <h1 class="page-title">{{ isEditMode ? '编辑文章' : '创作新文章' }}</h1>
      <p class="page-subtitle">{{ isEditMode ? '修改和完善您的文章内容' : '分享您的想法，创作优质内容' }}</p>
    </div>

    <!-- 主要内容区域 -->
    <div class="editor-content">
      <!-- 基本信息卡片 -->
      <el-card class="info-card" shadow="hover">
        <template #header>
          <h3 class="card-title">
            <el-icon class="title-icon"><Document /></el-icon>
            基本信息
          </h3>
        </template>
        
        <el-form label-position="top" class="article-form">
          <el-form-item label="文章标题" class="form-item-required" :error="formErrors.title">
            <el-input 
              v-model="form.title" 
              placeholder="请输入吸引人的标题..."
              size="large"
              maxlength="200"
              show-word-limit
              clearable
              data-field="title"
              :class="{ 'error-input': formErrors.title }"
              @blur="handleFieldBlur('title', form.title)"
              @input="clearFieldError('title')"
            >
              <template #prefix>
                <el-icon><EditPen /></el-icon>
              </template>
            </el-input>
            <div v-if="!formErrors.title" class="input-hint">
              <el-icon class="hint-icon"><InfoFilled /></el-icon>
              好的标题能够吸引更多读者点击阅读
            </div>
          </el-form-item>

          <el-form-item label="文章摘要" :error="formErrors.summary">
            <el-input 
              v-model="form.summary" 
              type="textarea" 
              :rows="3" 
              placeholder="简要描述文章内容，帮助读者快速了解..."
              maxlength="500"
              show-word-limit
              resize="vertical"
              data-field="summary"
              :class="{ 'error-input': formErrors.summary }"
              @blur="handleFieldBlur('summary', form.summary)"
              @input="clearFieldError('summary')"
            />
            <div v-if="!formErrors.summary" class="input-hint">
              摘要将显示在文章列表中，建议控制在100-200字
            </div>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 封面图片卡片 -->
      <el-card class="cover-card" shadow="hover">
        <template #header>
          <h3 class="card-title">
            <el-icon class="title-icon"><Picture /></el-icon>
            封面图片
          </h3>
        </template>

        <div class="cover-section">
          <!-- 上传区域 -->
          <div class="upload-section">
            <el-form-item label="上传封面图">
              <div class="upload-area">
                <el-upload
                  class="cover-uploader"
                  action="#"
                  :auto-upload="false"
                  :on-change="handleCoverSelect"
                  :show-file-list="false"
                  accept="image/*"
                  :disabled="uploading"
                >
                  <el-button 
                    type="primary" 
                    :loading="uploading"
                    :icon="uploading ? Loading : UploadFilled"
                    size="large"
                  >
                    {{ uploading ? '上传中...' : '选择封面图片' }}
                  </el-button>
                </el-upload>
                <div class="upload-progress" v-if="uploading">
                  <el-progress :percentage="uploadProgress" />
                </div>
              </div>
              <div class="input-hint">
                <el-icon class="hint-icon"><InfoFilled /></el-icon>
                支持 JPG、PNG、WebP 格式，建议尺寸 1200x630 像素，文件大小不超过 5MB
              </div>
            </el-form-item>
          </div>

          <!-- URL输入作为高级选项 -->
          <div class="url-section">
            <el-collapse>
              <el-collapse-item title="高级选项：使用图片链接" name="url">
                <el-form-item label="封面图片URL">
                  <el-input 
                    v-model="form.featured_image" 
                    placeholder="https://example.com/cover.jpg 或使用上传功能"
                    size="large"
                    clearable
                  >
                    <template #prefix>
                      <el-icon><Link /></el-icon>
                    </template>
                  </el-input>
                  <div class="input-hint">
                    直接输入图片网络地址，适合已有图片链接的用户
                  </div>
                </el-form-item>
              </el-collapse-item>
            </el-collapse>
          </div>

          <!-- 封面预览 -->
          <div v-if="form.featured_image" class="cover-preview">
            <label class="preview-label">封面预览</label>
            <div class="preview-container">
              <CoverImage 
                :src="form.featured_image" 
                alt="封面预览"
                container-class="preview-image-container"
                image-class="preview-image"
              />
            </div>
          </div>

          <!-- 焦点裁剪 -->
          <div v-if="form.featured_image" class="focal-section">
            <ImageFocalCropper v-model="form.featured_image" @focal-change="onFocal" />
          </div>
        </div>
      </el-card>

      <!-- 内容编辑卡片 -->
      <el-card class="content-card" shadow="hover">
        <template #header>
          <h3 class="card-title">
            <el-icon class="title-icon"><Edit /></el-icon>
            文章内容
          </h3>
        </template>
        
        <div class="editor-section">
          <div data-field="content_md" class="content_md-field">
            <VditorEditor ref="blockEditorRef" v-model="form.content_md" />
          </div>
          
          <!-- 键盘快捷键提示 -->
          <div class="keyboard-shortcuts-hint">
            <el-button 
              size="small" 
              text 
              @click="showKeyboardShortcuts"
              class="shortcuts-hint-btn"
            >
              <el-icon><Setting /></el-icon>
              快捷键提示 (Ctrl+K)
            </el-button>
            <span class="shortcuts-preview">
              Ctrl+S 保存 · Ctrl+Enter {{ isEditMode ? '更新' : '发布' }} · F1 帮助
            </span>
          </div>
        </div>
      </el-card>

      <!-- SEO 和标签卡片 -->
      <el-card class="seo-card" shadow="hover">
        <template #header>
          <h3 class="card-title">
            <el-icon class="title-icon"><Search /></el-icon>
            SEO 与分类
          </h3>
        </template>

        <el-form label-position="top" class="article-form">
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="SEO 标题" :error="formErrors.seo_title">
                <el-input 
                  v-model="form.seo_title" 
                  placeholder="搜索引擎显示的标题"
                  maxlength="60"
                  show-word-limit
                  clearable
                  data-field="seo_title"
                  :class="{ 'error-input': formErrors.seo_title }"
                  @blur="handleFieldBlur('seo_title', form.seo_title)"
                  @input="clearFieldError('seo_title')"
                />
                <div v-if="!formErrors.seo_title" class="input-hint">
                  如不填写，将使用文章标题作为SEO标题
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Meta 描述" :error="formErrors.seo_desc">
                <el-input 
                  v-model="form.seo_desc" 
                  placeholder="搜索引擎显示的描述"
                  maxlength="160"
                  show-word-limit
                  clearable
                  data-field="seo_desc"
                  :class="{ 'error-input': formErrors.seo_desc }"
                  @blur="handleFieldBlur('seo_desc', form.seo_desc)"
                  @input="clearFieldError('seo_desc')"
                />
                <div v-if="!formErrors.seo_desc" class="input-hint">
                  如不填写，将使用文章摘要作为描述
                </div>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="自定义 Slug" :error="formErrors.slug">
                <el-input 
                  v-model="form.slug" 
                  placeholder="custom-article-url"
                  clearable
                  data-field="slug"
                  :class="{ 'error-input': formErrors.slug }"
                  @blur="handleFieldBlur('slug', form.slug)"
                  @input="clearFieldError('slug')"
                />
                <div v-if="!formErrors.slug" class="input-hint">
                  自定义文章URL路径，如不填写将自动生成
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="文章标签">
                <div class="tags-selector">
                  <!-- 现有标签选择 -->
                  <el-select
                    v-model="selectedTags"
                    multiple
                    filterable
                    allow-create
                    default-first-option
                    reserve-keyword
                    placeholder="选择或创建标签"
                    class="tags-select"
                    @change="updateTagsRaw"
                    :loading="tagsLoading"
                  >
                    <el-option
                      v-for="tag in availableTags"
                      :key="tag.id"
                      :label="tag.name"
                      :value="tag.name"
                    >
                      <span class="tag-option">
                        <span class="tag-name">#{{ tag.name }}</span>
                        <span class="tag-count">({{ tag.article_count || 0 }})</span>
                      </span>
                    </el-option>
                  </el-select>
                  
                  <!-- 已选标签预览 -->
                  <div class="selected-tags" v-if="selectedTags.length > 0">
                    <el-tag
                      v-for="tag in selectedTags"
                      :key="tag"
                      closable
                      @close="removeTag(tag)"
                      class="selected-tag"
                    >
                      #{{ tag }}
                    </el-tag>
                  </div>
                </div>
                <div class="input-hint">
                  <el-icon class="hint-icon"><InfoFilled /></el-icon>
                  从现有标签中选择或创建新标签，建议3-5个标签
                </div>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 分类选择行 -->
          <el-row :gutter="24">
            <el-col :span="24">
              <el-form-item label="文章分类" :error="formErrors.category_id">
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
                  size="large"
                  @change="handleCategoryChange"
                  @recommendation-selected="handleRecommendationSelected"
                  @refresh-categories="loadCategories"
                  class="category-selector-field"
                />
                <div v-if="!formErrors.category_id" class="input-hint">
                  <el-icon class="hint-icon"><InfoFilled /></el-icon>
                  选择合适的分类有助于读者发现您的文章，支持AI智能推荐
                </div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <!-- 发布设置卡片 -->
      <el-card class="publish-card" shadow="hover">
        <template #header>
          <h3 class="card-title">
            <el-icon class="title-icon"><Clock /></el-icon>
            发布设置
          </h3>
        </template>

        <div class="publish-section">
          <div class="schedule-option">
            <el-switch 
              v-model="form.enable_schedule" 
              active-text="定时发布"
              inactive-text="立即发布"
              size="large"
            />
          </div>
          
          <div v-if="form.enable_schedule" class="schedule-picker">
            <el-form-item label="发布时间" :error="formErrors.scheduled_at">
              <el-date-picker 
                v-model="form.scheduled_at" 
                type="datetime" 
                placeholder="选择发布时间"
                size="large"
                style="width: 100%"
                data-field="scheduled_at"
                :class="{ 'error-input': formErrors.scheduled_at }"
                @blur="handleFieldBlur('scheduled_at', form.scheduled_at)"
                @change="clearFieldError('scheduled_at')"
              />
              <div v-if="!formErrors.scheduled_at" class="input-hint">
                <el-icon class="hint-icon"><InfoFilled /></el-icon>
                文章将在指定时间自动发布
              </div>
            </el-form-item>
          </div>
        </div>
      </el-card>

      <!-- 操作按钮区域 -->
      <div class="action-section">
        <el-button 
          type="primary" 
          size="large"
          :loading="loading" 
          @click.prevent="submit"
          class="submit-button"
        >
          <el-icon class="button-icon"><Check /></el-icon>
          {{ loading ? (isEditMode ? '更新中...' : '发布中...') : (isEditMode ? '更新文章' : '发布文章') }}
        </el-button>

        <el-button 
          size="large" 
          @click="saveDraft"
          :disabled="loading || autoSaving"
          :loading="autoSaving"
          class="draft-button"
        >
          <el-icon class="button-icon"><DocumentCopy /></el-icon>
          {{ autoSaving ? '保存中...' : '保存草稿' }}
        </el-button>
      </div>

      <!-- 自动保存状态提示 -->
      <div v-if="lastSaveTime || hasUnsavedChanges" class="autosave-status">
        <el-alert
          v-if="hasUnsavedChanges && !autoSaving"
          title="有未保存的更改"
          description="内容将在3秒后自动保存到本地草稿"
          type="warning"
          :closable="false"
          show-icon
          class="autosave-alert"
        />
        
        <el-alert
          v-if="autoSaving"
          title="正在自动保存..."
          type="info"
          :closable="false"
          show-icon
          class="autosave-alert"
        />
        
        <div v-if="lastSaveTime && !hasUnsavedChanges" class="save-time-info">
          <el-icon class="save-icon"><Check /></el-icon>
          <span class="save-text">上次保存: {{ formatSaveTime(lastSaveTime) }}</span>
        </div>
      </div>

      <!-- 错误提示 -->
      <el-alert 
        v-if="error" 
        :title="error" 
        type="error" 
        :closable="true"
        @close="error = ''"
        class="error-alert"
      />

      <el-alert 
        v-if="success" 
        :title="isEditMode ? '文章已重新提交审核！' : '文章已提交审核！'"
        :description="isEditMode ? '您的文章修改已保存并重新提交审核，编辑审核通过后将更新发布' : '您的文章已提交审核，编辑审核通过后将自动发布给读者'"
        type="warning" 
        :closable="true"
        @close="success = false"
        class="success-alert"
      />
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { API } from '../api';
import { UploadsService } from '../generated';
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router';
import { useUserStore } from '../stores/user';
import apiClient from '../apiClient';
import axios from 'axios';
import { setMeta } from '../composables/useMeta';
import { ElMessage, ElMessageBox } from 'element-plus';
import message, { MESSAGE_PRIORITY } from '../utils/message';
import VditorEditor from '../components/VditorEditor.vue';
import ImageUploader from '../components/ImageUploader.vue';
import ImageFocalCropper from '../components/ImageFocalCropper.vue';
import CoverImage from '../components/CoverImage.vue';
import CategorySelector from '../components/CategorySelector.vue';
import { ERROR_CODE_MAP } from '../governance/errorCodes.generated';
import { 
  Document, EditPen, InfoFilled, Picture, Link, UploadFilled, Loading,
  Edit, Search, Clock, Check, DocumentCopy, Setting
} from '@element-plus/icons-vue';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

// 编辑模式状态
const isEditMode = ref(false);
const editingArticleId = ref(null);
const originalArticle = ref(null);

// 表单状态
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
const categories = ref([]);
const categoryLoading = ref(false);

// 标签相关状态
const availableTags = ref([]);
const selectedTags = ref([]);
const tagsLoading = ref(false);

// 导航修复函数 - 简化版本
const handleDraftRestored = () => {
  console.log('📝 草稿恢复事件触发，确保导航状态正常');
  // 简单确认状态重置，不进行复杂操作
  hasUnsavedChanges.value = false;
  isRestoringDraft.value = false;
};

// 编辑器引用
const blockEditorRef = ref(null);

// 表单验证状态
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

// 上传状态
const uploading = ref(false);
const uploadProgress = ref(0);

// 自动保存状态
const autoSaving = ref(false);
const lastSaveTime = ref(null);
const autoSaveInterval = ref(null);
const hasUnsavedChanges = ref(false);
const isRestoringDraft = ref(false); // 标记是否正在恢复草稿
const AUTOSAVE_DELAY = 3000; // 3秒后自动保存
// 工具函数
function mapErr(code, fallback) { 
  return ERROR_CODE_MAP.get(code) || fallback; 
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
function formatSaveTime(time) {
  if (!time) return '';
  
  const now = new Date();
  const diff = now - time;
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  
  return time.toLocaleDateString() + ' ' + time.toLocaleTimeString();
}

// 图片处理函数
function insertImage(meta) {
  const tag = `![${meta.width || ''}x${meta.height || ''}](${meta.url})`;
  form.value.content_md = (form.value.content_md || '') + (form.value.content_md ? '\n' : '') + tag + '\n';
}

function onFeaturedCandidate(meta) {
  // 若尚未设置封面图，首次上传默认填入 featured_image
  if (!form.value.featured_image && meta?.url) { 
    form.value.featured_image = meta.url; 
  }
}

function onFocal(f) { 
  form.value.featured_focal_x = f.x; 
  form.value.featured_focal_y = f.y; 
}

// 加载文章数据用于编辑
async function loadArticleForEdit(articleId) {
  try {
    console.log('正在加载文章数据用于编辑:', articleId);
    loading.value = true;
    
    const response = await apiClient.get(`/articles/${articleId}`);
    
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
    message.critical('加载文章失败: ' + error.message);
    router.push('/');
  } finally {
    loading.value = false;
  }
}

// 封面图片上传处理
async function handleCoverSelect(file) {
  if (!file || !file.raw) return;
  
  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.raw.type)) {
    message.warning('不支持的文件格式，请选择 JPG、PNG 或 WebP 格式的图片');
    return;
  }
  
  // 验证文件大小 (5MB)
  const maxSize = 5 * 1024 * 1024;
  if (file.raw.size > maxSize) {
    message.warning('文件过大，请选择小于 5MB 的图片');
    return;
  }
  
  uploading.value = true;
  uploadProgress.value = 0;
  error.value = '';
  
  try {
    // 模拟上传进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10;
      }
    }, 100);
    
    const response = await UploadsService.postApiV1UploadsImage({
      file: file.raw
    });
    
    clearInterval(progressInterval);
    uploadProgress.value = 100;
    
    if (response.data?.url) {
      form.value.featured_image = response.data.url;
      message.success({
        message: '🖼️ 封面图片上传成功！',
        duration: 3000
      });
    } else {
      error.value = '上传成功但未获取到图片地址';
    }
  } catch (e) {
    console.error('Cover upload error:', e);
    
    if (e.response?.data?.message) {
      error.value = `上传失败: ${e.response.data.message}`;
    } else {
      error.value = '封面图片上传失败，请稍后重试';
    }
  } finally {
    uploading.value = false;
    uploadProgress.value = 0;
  }
}
// 表单验证功能
function validateField(fieldName, value) {
  const rules = validationRules[fieldName];
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
  const errors = {};
  let hasErrors = false;
  
  // 验证所有字段
  Object.keys(validationRules).forEach(fieldName => {
    const value = form.value[fieldName];
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

function clearFieldError(fieldName) {
  if (formErrors.value[fieldName]) {
    delete formErrors.value[fieldName];
    formErrors.value = { ...formErrors.value };
  }
}

// 实时验证
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
      resp = await apiClient.put(`/articles/${editingArticleId.value}`, payload);
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
    let publishType = 'success';
    
    if (!isEditMode.value) {
      // 新文章需要提交审核
      try {
        await apiClient.post(`/articles/${articleId}/submit`);
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
          background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%) !important;
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
          background: linear-gradient(135deg, #10b981, #059669) !important;
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
    console.error('❌ Error response:', e.response);
    console.error('❌ Error response data:', e.response?.data);
    console.error('❌ Error status:', e.response?.status);
    console.error('❌ Error message:', e.message);
    
    const code = e.body?.code || e.response?.data?.code;
    const mappedError = mapErr(code, '文章发布失败');
    
    // 详细的错误处理
    if (e.response?.status === 500) {
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
    } else if (e.response?.data?.message) {
      error.value = e.response.data.message;
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
    console.error('❌ 加载分类列表失败:', error);
    console.error('❌ 错误详情:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
      url: error.config?.url
    });
    
    // 如果公开接口失败，尝试使用认证接口
    console.log('🔄 公开接口失败，尝试使用认证接口...');
    try {
      const authResponse = await apiClient.get('/api/v1/categories/');
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
    
    message.critical(`加载分类列表失败: ${error.response?.data?.message || error.message || '网络错误'}`);
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
function handleCategoryChange(categoryId) {
  form.value.category_id = categoryId;
  clearFieldError('category_id');
  
  if (categoryId) {
    const selectedCategory = categories.value.find(cat => cat.id === categoryId);
    if (selectedCategory) {
      console.log('🏷️ 已选择分类:', selectedCategory.name);
      
      // 触发自动保存（如果有其他内容）
      if (form.value.title || form.value.content_md) {
        markAsChanged();
      }
    }
  }
}

// 加载可用标签
async function loadAvailableTags() {
  try {
    tagsLoading.value = true;
    const response = await apiClient.get('/taxonomy/stats');
    
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
function updateTagsRaw() {
  form.value.tags_raw = selectedTags.value.join(', ');
  console.log('🏷️ 标签已更新:', selectedTags.value);
  
  // 触发自动保存
  if (form.value.title || form.value.content_md) {
    markAsChanged();
  }
}

// 移除标签
function removeTag(tag) {
  const index = selectedTags.value.indexOf(tag);
  if (index > -1) {
    selectedTags.value.splice(index, 1);
    updateTagsRaw();
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
      }).sort((a, b) => new Date(b.savedAt) - new Date(a.savedAt));
      
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
    const hoursDiff = (now - saveTime) / (1000 * 60 * 60);
    
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
            background: linear-gradient(135deg, #fefbff 0%, #f8fafc 100%) !important;
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
            background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
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
            if (key !== 'savedAt' && key !== 'id' && key !== 'status' && 
                key !== 'content_md' && form.value.hasOwnProperty(key)) {
              form.value[key] = draftData[key];
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
          console.error('草稿恢复过程中出现错误:', error);
          
          // 检查是否是Vue响应式系统的错误（这种情况下数据可能已经恢复成功）
          const isVueRenderError = error.message && error.message.includes('__vnode');
          
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
          document.querySelector('.cover-uploader input[type="file"]')?.click();
        }
        break;
        
      case 'l':
        // Ctrl+L: 插入链接  
        if (e.shiftKey) {
          e.preventDefault();
          // 聚焦到编辑器区域
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
  const articleId = route.params.id;
  if (articleId && route.meta.editMode) {
    isEditMode.value = true;
    editingArticleId.value = parseInt(articleId);
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
/* 文章编辑器容器 */
.article-editor-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem 1rem 0rem;
  background: linear-gradient(135deg, rgb(248 250 252) 0%, rgb(241 245 249) 100%);
  min-height: calc(100vh - 80px);
}

/* 页面头部 */
.editor-header {
  text-align: center;
  margin-bottom: 2.5rem;
  padding: 2rem 0;
  background: linear-gradient(135deg, rgb(255 255 255) 0%, rgb(248 250 252) 100%);
  border-radius: 1rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.page-title {
  font-size: 2.25rem;
  font-weight: 700;
  color: rgb(17 24 39);
  margin-bottom: 0.5rem;
  letter-spacing: -0.025em;
}

.page-subtitle {
  color: rgb(107 114 128);
  font-size: 1.125rem;
  margin: 0;
  line-height: 1.6;
}

/* 主要内容区域 */
.editor-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* 卡片通用样式 */
.info-card,
.cover-card,
.content-card,
.seo-card,
.publish-card {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  transition: all 0.3s ease;
  border: 1px solid rgb(229 231 235);
}

.info-card:hover,
.cover-card:hover,
.content-card:hover,
.seo-card:hover,
.publish-card:hover {
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  transform: translateY(-2px);
}

/* 卡片标题 */
.card-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: rgb(17 24 39);
  margin: 0;
}

.title-icon {
  color: rgb(59 130 246);
  font-size: 1.5rem;
}

/* 表单样式 */
.article-form {
  width: 100%;
}

.form-item-required :deep(.el-form-item__label)::before {
  content: '*';
  color: rgb(239 68 68);
  margin-right: 4px;
}

/* ====== 封面图片卡片样式 ====== */
.cover-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.upload-section {
  flex: 1;
}

.upload-area {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.cover-uploader {
  width: 100%;
}

.upload-progress {
  width: 100%;
}

.url-section {
  margin-top: 1rem;
}

/* 封面预览 */
.cover-preview {
  padding: 1.5rem;
  background: rgb(248 250 252);
  border-radius: 0.75rem;
  border: 1px solid rgb(229 231 235);
}

.preview-label {
  display: block;
  font-weight: 600;
  color: rgb(17 24 39);
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.preview-container {
  max-width: 500px;
  width: 100%;
}

.preview-image-container {
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  /* 设置固定的纵横比容器 */
  aspect-ratio: 16 / 9;
  max-height: 280px;
  position: relative;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  /* 确保图片填满容器但保持比例 */
}

.focal-section {
  margin-top: 1rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .preview-container {
    max-width: 100%;
  }
  
  .preview-image-container {
    max-height: 200px;
    aspect-ratio: 16 / 10; /* 移动端稍微调整比例 */
  }
}

/* ====== 内容编辑卡片样式 ====== */
.editor-section {
  width: 100%;
}

/* ====== 发布设置卡片样式 ====== */
.publish-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.schedule-option {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.schedule-picker {
  width: 100%;
}

/* ====== 操作按钮区域 ====== */
.action-section {
  display: flex;
  gap: 1rem;
  justify-content: center;
  padding: 1.5rem 0;
  border-top: 1px solid rgb(229 231 235);
  margin-top: 1rem;
}

.submit-button {
  background: linear-gradient(135deg, rgb(34 197 94), rgb(22 163 74));
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 0.75rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgb(34 197 94 / 0.25);
}

.submit-button:hover {
  background: linear-gradient(135deg, rgb(22 163 74), rgb(21 128 61));
  transform: translateY(-2px);
  box-shadow: 0 8px 12px rgb(34 197 94 / 0.35);
}

.draft-button {
  background: rgb(249 250 251);
  border: 1px solid rgb(209 213 219);
  color: rgb(75 85 99);
  padding: 0.75rem 2rem;
  border-radius: 0.75rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.draft-button:hover {
  background: rgb(243 244 246);
  border-color: rgb(156 163 175);
  color: rgb(55 65 81);
}

.button-icon {
  margin-right: 0.5rem;
}

/* ====== 状态提示 ====== */
.autosave-status {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
}

.autosave-alert {
  border-radius: 0.75rem;
  margin-bottom: 1rem;
}

.save-time-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgb(240 253 244);
  border: 1px solid rgb(187 247 208);
  border-radius: 0.75rem;
  font-size: 0.875rem;
}

.save-icon {
  color: rgb(34 197 94);
  font-size: 1rem;
}

.save-text {
  color: rgb(21 128 61);
  font-weight: 500;
}

.error-alert,
.success-alert {
  margin-top: 1.5rem;
  border-radius: 0.75rem;
}

/* ====== 输入提示 ====== */
.input-hint {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: rgb(107 114 128);
  line-height: 1.4;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.hint-icon {
  color: rgb(59 130 246);
  font-size: 1rem;
  margin-top: 0.1rem;
  flex-shrink: 0;
}

/* ===== 分类选择器样式 ===== */

.category-selector-field {
  width: 100%;
}

.category-selector-field :deep(.category-selector) {
  width: 100%;
}

.category-selector-field :deep(.selector-main) {
  margin-bottom: 0;
}

.category-selector-field :deep(.ai-recommend-btn) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  font-weight: 500;
  transition: all 0.3s ease;
}

.category-selector-field :deep(.ai-recommend-btn:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.category-selector-field :deep(.recommendations-panel) {
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  margin-top: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.category-selector-field :deep(.selection-info) {
  margin-top: 12px;
}

.category-selector-field :deep(.selected-category) {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #7dd3fc;
  color: #0c4a6e;
  font-size: 14px;
}

/* ====== Element Plus 样式覆盖 ====== */
:deep(.el-card__header) {
  padding: 1.5rem 1.5rem 1rem;
  border-bottom: 1px solid rgb(243 244 246);
}

:deep(.el-card__body) {
  padding: 1.5rem;
}

:deep(.el-form-item__label) {
  font-weight: 600;
  color: rgb(17 24 39);
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

:deep(.el-input__wrapper) {
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
  transition: all 0.2s ease;
}

:deep(.el-input__wrapper):hover {
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgb(59 130 246 / 0.3), 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

:deep(.el-textarea__inner) {
  border-radius: 0.5rem;
  transition: all 0.2s ease;
}

:deep(.el-button) {
  border-radius: 0.5rem;
  font-weight: 500;
}

/* 折叠面板样式 */
:deep(.el-collapse) {
  border: none;
  border-radius: 0.5rem;
  background: rgb(248 250 252);
}

:deep(.el-collapse-item__header) {
  background: rgb(248 250 252);
  border: none;
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  color: rgb(107 114 128);
  font-weight: 500;
}

:deep(.el-collapse-item__content) {
  background: rgb(248 250 252);
  border: none;
  padding: 0 1rem 1rem;
}

:deep(.el-collapse-item__wrap) {
  border: none;
}

/* 上传按钮样式 */
:deep(.el-upload) {
  width: 100%;
}

:deep(.el-upload .el-button) {
  width: 100%;
  border-radius: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

/* 进度条样式 */
:deep(.el-progress-bar) {
  background: rgb(243 244 246);
  border-radius: 0.5rem;
}

:deep(.el-progress-bar__inner) {
  background: linear-gradient(135deg, rgb(34 197 94), rgb(22 163 74));
  border-radius: 0.5rem;
}

/* ====== 键盘快捷键提示 ====== */
.keyboard-shortcuts-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: rgb(249 250 251);
  border-top: 1px solid rgb(229 231 235);
  border-radius: 0 0 0.75rem 0.75rem;
  margin-top: -1px;
}

.shortcuts-hint-btn {
  font-size: 0.75rem !important;
  padding: 0.375rem 0.75rem !important;
  border-radius: 0.375rem !important;
  color: rgb(59 130 246) !important;
  transition: all 0.2s ease;
}

.shortcuts-hint-btn:hover {
  background: rgb(239 246 255) !important;
}

.shortcuts-hint-btn .el-icon {
  margin-right: 0.25rem;
  font-size: 0.875rem;
}

.shortcuts-preview {
  font-size: 0.75rem;
  color: rgb(107 114 128);
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
}

/* 快捷键提示消息样式 */
:deep(.keyboard-shortcuts-message) {
  max-width: 400px;
  white-space: pre-line;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}

/* ====== 表单验证样式 ====== */
.error-input :deep(.el-input__wrapper) {
  border-color: rgb(239 68 68) !important;
  box-shadow: 0 0 0 1px rgb(239 68 68 / 0.3) !important;
}

.error-input :deep(.el-textarea__inner) {
  border-color: rgb(239 68 68) !important;
  box-shadow: 0 0 0 1px rgb(239 68 68 / 0.3) !important;
}

.error-input :deep(.el-input__wrapper):hover {
  border-color: rgb(220 38 38) !important;
  box-shadow: 0 0 0 1px rgb(239 68 68 / 0.5) !important;
}

.error-input :deep(.el-textarea__inner):hover {
  border-color: rgb(220 38 38) !important;
  box-shadow: 0 0 0 1px rgb(239 68 68 / 0.5) !important;
}

/* 错误信息样式 */
:deep(.el-form-item__error) {
  color: rgb(239 68 68);
  font-size: 0.75rem;
  font-weight: 500;
  margin-top: 0.25rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

:deep(.el-form-item__error):before {
  content: '⚠️';
  font-size: 0.875rem;
}

/* 成功状态样式 */
.success-input :deep(.el-input__wrapper) {
  border-color: rgb(34 197 94) !important;
  box-shadow: 0 0 0 1px rgb(34 197 94 / 0.3) !important;
}

.success-input :deep(.el-textarea__inner) {
  border-color: rgb(34 197 94) !important;
  box-shadow: 0 0 0 1px rgb(34 197 94 / 0.3) !important;
}

/* 表单项动画 */
.el-form-item {
  transition: all 0.3s ease;
}

.el-form-item.is-error {
  animation: shakeError 0.5s ease-in-out;
}

@keyframes shakeError {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

/* 验证提示特殊样式 */
.validation-summary {
  background: rgb(254 242 242);
  border: 1px solid rgb(254 226 226);
  border-radius: 0.75rem;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.validation-summary-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: rgb(239 68 68);
  font-weight: 600;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.validation-summary-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.validation-summary-list li {
  color: rgb(185 28 28);
  font-size: 0.75rem;
  margin-bottom: 0.25rem;
  padding-left: 1rem;
  position: relative;
}

.validation-summary-list li:before {
  content: '•';
  position: absolute;
  left: 0;
  color: rgb(239 68 68);
  font-weight: bold;
}

/* ====== 响应式设计 ====== */
@media (max-width: 768px) {
  .article-editor-container {
    padding: 1rem 0.75rem;
  }
  
  .page-title {
    font-size: 1.875rem;
  }
  
  .page-subtitle {
    font-size: 1rem;
  }
  
  .action-section {
    flex-direction: column;
    align-items: stretch;
  }
  
  .submit-button,
  .draft-button {
    width: 100%;
  }

  :deep(.el-row) {
    --el-row-gutter: 12px;
  }
  
  :deep(.el-col) {
    margin-bottom: 1rem;
  }
}

/* 错误字段高亮动画 */
.field-error-highlight {
  animation: errorPulse 0.6s ease-in-out;
  border: 2px solid #f56565 !important;
  border-radius: 4px;
}

@keyframes errorPulse {
  0%, 100% { 
    border-color: #f56565; 
    box-shadow: 0 0 0 0 rgba(245, 101, 101, 0.7);
  }
  50% { 
    border-color: #e53e3e; 
    box-shadow: 0 0 0 8px rgba(245, 101, 101, 0);
  }
}

@media (max-width: 640px) {
  .editor-header {
    padding: 1.5rem 1rem;
  }
  
  /* Element Plus 卡片内边距调整 */
  :deep(.el-card__body) {
    padding: 1.25rem;
  }
  
  /* Element Plus 表单项间距调整 */
  :deep(.el-form-item) {
    margin-bottom: 1.25rem;
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
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%) !important;
  padding: 32px 24px 16px !important;
  text-align: center !important;
  border-bottom: 1px solid #f0f9ff !important;
  position: relative !important;
}

.publish-success-dialog.el-message-box .el-message-box__title {
  font-size: 24px !important;
  font-weight: 700 !important;
  color: #065f46 !important;
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
  background: linear-gradient(135deg, #10b981, #059669) !important;
  border: none !important;
  border-radius: 12px !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  padding: 14px 28px !important;
  font-size: 15px !important;
  min-width: 120px !important;
  height: auto !important;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
  transition: all 0.2s ease !important;
}

.publish-success-dialog.el-message-box .dialog-confirm-btn:hover {
  background: linear-gradient(135deg, #059669, #047857) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4) !important;
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

/* ===== 标签选择器样式 ===== */
.tags-selector {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tags-select {
  width: 100%;
}

.tag-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.tag-name {
  font-weight: 500;
  color: #374151;
}

.tag-count {
  font-size: 0.75rem;
  color: #6b7280;
  background: rgba(59, 130, 246, 0.1);
  padding: 2px 6px;
  border-radius: 12px;
  margin-left: 8px;
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(59, 130, 246, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 8px;
  min-height: 45px;
  transition: all 0.3s ease;
}

.selected-tags:empty::after {
  content: '暂无选择标签';
  color: #9ca3af;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  height: 100%;
}

.selected-tag {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border-color: #3b82f6;
  color: white;
  font-weight: 500;
  transition: all 0.3s ease;
}

.selected-tag:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.selected-tag .el-tag__close {
  color: rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
}

.selected-tag .el-tag__close:hover {
  color: white;
  background-color: rgba(255, 255, 255, 0.2);
}

/* 选择器下拉样式优化 */
:deep(.el-select-dropdown__item.hover) {
  background-color: rgba(59, 130, 246, 0.1);
}

:deep(.el-select-dropdown__item.selected) {
  background-color: rgba(59, 130, 246, 0.15);
  font-weight: 600;
}

:deep(.el-select__tags) {
  max-height: 80px;
  overflow-y: auto;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .selected-tags {
    padding: 0.5rem;
    min-height: 40px;
  }
  
  .selected-tag {
    font-size: 0.8rem;
  }
  
  .tag-option {
    font-size: 0.875rem;
  }
}
</style>
