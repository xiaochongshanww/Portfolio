<template>
  <div class="profile-page-container">
    <!-- 页面头部 -->
    <div class="profile-header">
      <h1 class="page-title">个人设置</h1>
      <p class="page-subtitle">管理您的个人信息和偏好设置</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="!loaded" class="loading-container">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载中...</p>
    </div>

    <!-- 主要内容 -->
    <div v-else class="profile-content">
      <!-- 头像卡片 -->
      <el-card class="avatar-card" shadow="hover">
        <template #header>
          <h3 class="card-title">
            <el-icon class="title-icon"><Avatar /></el-icon>
            头像设置
          </h3>
        </template>
        
        <div class="avatar-section">
          <div class="avatar-preview">
            <div class="avatar-container">
              <img 
                v-if="form.avatar && !avatarError" 
                :src="form.avatar" 
                alt="头像预览"
                class="avatar-img"
                @error="handleAvatarError"
                @load="handleAvatarLoad"
              />
              <div v-else class="avatar-placeholder">
                <el-icon class="placeholder-icon"><User /></el-icon>
              </div>
            </div>
            <div class="avatar-info">
              <p class="avatar-status" v-if="form.avatar">
                <span v-if="avatarLoading" class="status-loading">检测中...</span>
                <span v-else-if="avatarError" class="status-error">头像加载失败</span>
                <span v-else class="status-success">头像正常</span>
              </p>
            </div>
          </div>
          
          <div class="avatar-controls">
            <!-- 主要上传方式：文件上传 -->
            <div class="upload-section">
              <el-form-item label="上传头像">
                <div class="upload-area">
                  <el-upload
                    class="avatar-uploader"
                    action="#"
                    :auto-upload="false"
                    :on-change="handleFileSelect"
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
                      {{ uploading ? '上传中...' : '选择图片' }}
                    </el-button>
                  </el-upload>
                  <div class="upload-progress" v-if="uploading">
                    <el-progress :percentage="uploadProgress" />
                  </div>
                </div>
                <div class="input-hint">
                  <el-icon class="hint-icon"><InfoFilled /></el-icon>
                  支持 JPG、PNG、WebP 格式，文件大小不超过 5MB，建议尺寸 200x200 像素
                </div>
              </el-form-item>
            </div>

            <!-- 高级选项：URL 输入 -->
            <div class="url-section">
              <el-collapse>
                <el-collapse-item title="高级选项：使用图片链接" name="url">
                  <el-form-item label="头像URL">
                    <el-input 
                      v-model="form.avatar" 
                      placeholder="https://example.com/avatar.jpg" 
                      size="large"
                      clearable
                    >
                      <template #prefix>
                        <el-icon><Link /></el-icon>
                      </template>
                    </el-input>
                    <div class="input-hint">
                      直接输入头像图片的网络地址，适合已有图片链接的用户
                    </div>
                  </el-form-item>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 基本信息卡片 -->
      <el-card class="basic-info-card" shadow="hover">
        <template #header>
          <h3 class="card-title">
            <el-icon class="title-icon"><User /></el-icon>
            基本信息
          </h3>
        </template>

        <el-form :model="form" label-position="top" class="profile-form">
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="昵称">
                <el-input 
                  v-model="form.nickname" 
                  maxlength="80" 
                  placeholder="请输入您的昵称"
                  size="large"
                  show-word-limit
                  clearable
                >
                  <template #prefix>
                    <el-icon><EditPen /></el-icon>
                  </template>
                </el-input>
                <div class="input-hint">
                  昵称将在文章和评论中显示，建议使用真实姓名或常用网名
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <div class="nickname-preview">
                <label class="preview-label">显示效果预览</label>
                <div class="preview-container">
                  <div class="preview-name">{{ getDisplayPreview() }}</div>
                  <div class="preview-hint">其他用户看到的名称</div>
                </div>
              </div>
            </el-col>
          </el-row>

          <el-form-item label="个人简介">
            <el-input 
              v-model="form.bio" 
              type="textarea" 
              :rows="4" 
              maxlength="2000" 
              placeholder="介绍一下您自己..."
              show-word-limit
              resize="vertical"
            />
            <div class="input-hint">
              简介将显示在您的个人主页，让其他用户更好地了解您
            </div>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 社交链接卡片 -->
      <el-card class="social-links-card" shadow="hover">
        <template #header>
          <h3 class="card-title">
            <el-icon class="title-icon"><Link /></el-icon>
            社交链接
          </h3>
        </template>

        <div class="social-section">
          <el-form-item label="社交链接配置">
            <el-input 
              v-model="form.social_links_raw" 
              type="textarea" 
              :rows="6" 
              placeholder='请输入 JSON 格式的社交链接：
{
  "github": "https://github.com/username",
  "twitter": "https://twitter.com/username",
  "linkedin": "https://linkedin.com/in/username"
}'
              class="json-input"
            />
            <div class="input-hint">
              <el-icon class="hint-icon"><InfoFilled /></el-icon>
              支持的平台：GitHub, Twitter, LinkedIn, WeChat 等
            </div>
          </el-form-item>

          <!-- JSON 预览 -->
          <div v-if="parsedSocialLinks" class="social-preview">
            <label class="preview-label">链接预览</label>
            <div class="social-items">
              <div 
                v-for="(url, platform) in parsedSocialLinks" 
                :key="platform" 
                class="social-item"
              >
                <el-icon class="social-icon"><Link /></el-icon>
                <span class="platform-name">{{ platform }}</span>
                <span class="platform-url">{{ url }}</span>
              </div>
            </div>
          </div>

          <!-- JSON 错误提示 -->
          <el-alert 
            v-if="socialLinksError" 
            :title="socialLinksError" 
            type="warning" 
            :closable="false"
            class="json-error-alert"
          />
        </div>
      </el-card>

      <!-- 操作按钮区域 -->
      <div class="action-section">
        <el-button 
          type="primary" 
          size="large" 
          :loading="saving" 
          @click="save"
          class="save-button"
        >
          <el-icon class="button-icon"><Check /></el-icon>
          {{ saving ? '保存中...' : '保存设置' }}
        </el-button>

        <el-button 
          size="large" 
          @click="resetForm"
          :disabled="saving"
          class="reset-button"
        >
          <el-icon class="button-icon"><RefreshLeft /></el-icon>
          重置
        </el-button>
      </div>

      <!-- 状态提示 -->
      <el-alert 
        v-if="error" 
        :title="error" 
        type="error" 
        :closable="true"
        @close="error = ''"
        class="error-alert"
      />

      <el-alert 
        v-if="saved" 
        title="设置已保存"
        description="您的个人信息已成功更新"
        type="success" 
        :closable="true"
        @close="saved = false"
        class="success-alert"
      />
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue';
import { UsersService, UploadsService } from '../generated';
import { useNotify } from '../composables/useNotify';
import { setMeta } from '../composables/useMeta';
import { getUserDisplayName } from '../utils/userDisplay';
import { ElMessage } from 'element-plus';
import { useUserStore } from '../stores/user';
import { 
  Avatar, User, Link, EditPen, Check, RefreshLeft, InfoFilled,
  UploadFilled, Loading
} from '@element-plus/icons-vue';

const { pushError } = useNotify();
const userStore = useUserStore();

// 基础状态
const loaded = ref(false);
const saving = ref(false);
const saved = ref(false);
const error = ref('');

// 头像相关状态
const avatarError = ref(false);
const avatarLoading = ref(false);

// 上传相关状态
const uploading = ref(false);
const uploadProgress = ref(0);

// 表单数据
const form = ref({ 
  nickname: '', 
  bio: '', 
  avatar: '', 
  social_links_raw: '' 
});

// 原始数据备份（用于重置）
const originalForm = ref({});

// 社交链接解析
const parsedSocialLinks = computed(() => {
  if (!form.value.social_links_raw.trim()) return null;
  
  try {
    const parsed = JSON.parse(form.value.social_links_raw);
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      return parsed;
    }
    return null;
  } catch (e) {
    return null;
  }
});

// 社交链接错误
const socialLinksError = computed(() => {
  if (!form.value.social_links_raw.trim()) return null;
  
  try {
    const parsed = JSON.parse(form.value.social_links_raw);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return 'JSON 格式应为对象 {...}，不是数组或其他类型';
    }
    return null;
  } catch (e) {
    return `JSON 格式错误: ${e.message}`;
  }
});

// 加载用户数据
async function load() {
  try {
    const r = await UsersService.getApiV1UsersMe();
    const d = r.data?.data || r.data || r;
    
    form.value.nickname = d.nickname || '';
    form.value.bio = d.bio || '';
    form.value.avatar = d.avatar || '';
    
    if (d.social_links) {
      form.value.social_links_raw = JSON.stringify(d.social_links, null, 2);
    }
    
    // 备份原始数据
    originalForm.value = { ...form.value };
  } catch (e) {
    pushError('加载失败');
  } finally {
    loaded.value = true;
  }
}

// 保存设置
async function save() {
  saving.value = true;
  error.value = '';
  saved.value = false;
  
  try {
    let socialLinks;
    if (form.value.social_links_raw.trim()) {
      try {
        socialLinks = JSON.parse(form.value.social_links_raw);
        if (typeof socialLinks !== 'object' || socialLinks === null || Array.isArray(socialLinks)) {
          error.value = '社交链接格式无效，应为对象格式';
          return;
        }
      } catch (e) {
        error.value = '社交链接 JSON 格式无效';
        return;
      }
    }
    
    const payload = {
      nickname: form.value.nickname || undefined,
      bio: form.value.bio || undefined,
      avatar: form.value.avatar || undefined,
      social_links: socialLinks
    };
    
    await UsersService.patchApiV1UsersMe(payload);
    saved.value = true;
    
    // 更新原始数据备份
    originalForm.value = { ...form.value };
    
    // 更新全局用户状态，让头像等信息同步到其他组件
    await userStore.fetchUserInfo();
  } catch (e) {
    console.error('Profile save error:', e);
    
    // 提取详细错误信息
    if (e.response?.data) {
      const errorData = e.response.data;
      if (errorData.message) {
        error.value = errorData.message;
        // 如果有具体的验证错误信息，也显示出来
        if (errorData.data && typeof errorData.data === 'string') {
          error.value += `: ${errorData.data}`;
        }
      } else {
        error.value = '保存失败，请检查输入信息';
      }
    } else if (e.message) {
      error.value = `保存失败: ${e.message}`;
    } else {
      error.value = '保存失败，请稍后重试';
    }
  } finally {
    saving.value = false;
  }
}

// 重置表单
function resetForm() {
  form.value = { ...originalForm.value };
  error.value = '';
  saved.value = false;
  avatarError.value = false;
}

// 头像处理函数
function handleAvatarError() {
  avatarError.value = true;
  avatarLoading.value = false;
}

function handleAvatarLoad() {
  avatarError.value = false;
  avatarLoading.value = false;
}

// 文件上传处理函数
async function handleFileSelect(file) {
  if (!file || !file.raw) return;
  
  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.raw.type)) {
    error.value = '不支持的文件格式，请选择 JPG、PNG 或 WebP 格式的图片';
    return;
  }
  
  // 验证文件大小 (5MB)
  const maxSize = 5 * 1024 * 1024;
  if (file.raw.size > maxSize) {
    error.value = '文件过大，请选择小于 5MB 的图片';
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
      // 直接使用后端返回的相对路径URL，代理会自动转发
      form.value.avatar = response.data.url;
      
      // 重置头像错误状态
      avatarError.value = false;
      avatarLoading.value = true;
      
      // 自动保存头像到后端
      try {
        await UsersService.patchApiV1UsersMe({
          avatar: form.value.avatar
        });
        
        // 更新全局用户状态，让右上角头像立即更新
        await userStore.fetchUserInfo();
        
        // 更新原始数据备份
        originalForm.value.avatar = form.value.avatar;
        
        ElMessage.success('头像上传并保存成功！');
      } catch (saveError) {
        console.error('头像自动保存失败:', saveError);
        ElMessage.warning('头像上传成功，但自动保存失败，请手动点击保存按钮');
      }
    } else {
      error.value = '上传成功但未获取到图片地址';
    }
  } catch (e) {
    console.error('Avatar upload error:', e);
    
    if (e.response?.data?.message) {
      error.value = `上传失败: ${e.response.data.message}`;
    } else {
      error.value = '头像上传失败，请稍后重试';
    }
  } finally {
    uploading.value = false;
    uploadProgress.value = 0;
  }
}

// 获取显示预览
function getDisplayPreview() {
  const mockUser = {
    nickname: form.value.nickname,
    email: 'user@example.com', // 示例邮箱
    id: 123
  };
  return getUserDisplayName(mockUser, { maxLength: 20 });
}

// 组件挂载
onMounted(() => {
  setMeta({ 
    title: '个人设置', 
    description: '管理您的个人信息和偏好设置' 
  });
  load();
});
</script>
<style scoped>
/* 页面容器 */
.profile-page-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
  background: linear-gradient(135deg, rgb(248 250 252) 0%, rgb(241 245 249) 100%);
  min-height: calc(100vh - 80px);
}

/* 页面头部 */
.profile-header {
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

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 0;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgb(229 231 235);
  border-top: 4px solid rgb(59 130 246);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  color: rgb(107 114 128);
  font-size: 1rem;
}

/* 主要内容区域 */
.profile-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* 卡片通用样式 */
.avatar-card,
.basic-info-card,
.social-links-card {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  transition: all 0.3s ease;
  border: 1px solid rgb(229 231 235);
}

.avatar-card:hover,
.basic-info-card:hover,
.social-links-card:hover {
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

/* ====== 头像卡片样式 ====== */
.avatar-section {
  display: flex;
  gap: 2rem;
  align-items: flex-start;
}

.avatar-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  min-width: 120px;
}

.avatar-container {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 8px 16px rgb(0 0 0 / 0.15);
  transition: transform 0.3s ease;
}

.avatar-container:hover {
  transform: scale(1.05);
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgb(59 130 246), rgb(139 92 246));
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-icon {
  color: white;
  font-size: 2.5rem;
}

.avatar-info {
  text-align: center;
}

.avatar-status {
  font-size: 0.875rem;
  margin: 0;
}

.status-loading { color: rgb(251 191 36); }
.status-error { color: rgb(239 68 68); }
.status-success { color: rgb(34 197 94); }

.avatar-controls {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 上传区域样式 */
.upload-section {
  flex: 1;
}

.upload-area {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.avatar-uploader {
  width: 100%;
}

.upload-progress {
  width: 100%;
}

/* URL 输入区域样式 */
.url-section {
  margin-top: 1rem;
}

/* Element Plus 折叠面板样式覆盖 */
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

/* ====== 基本信息卡片样式 ====== */
.profile-form {
  width: 100%;
}

.nickname-preview {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.preview-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgb(75 85 99);
}

.preview-container {
  padding: 1rem;
  background: rgb(248 250 252);
  border: 2px dashed rgb(203 213 225);
  border-radius: 0.5rem;
  text-align: center;
}

.preview-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: rgb(17 24 39);
  margin-bottom: 0.25rem;
}

.preview-hint {
  font-size: 0.75rem;
  color: rgb(107 114 128);
}

/* ====== 社交链接卡片样式 ====== */
.social-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.json-input :deep(.el-textarea__inner) {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  border-radius: 0.5rem;
}

.social-preview {
  padding: 1rem;
  background: rgb(248 250 252);
  border-radius: 0.75rem;
  border: 1px solid rgb(229 231 235);
}

.social-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.social-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: white;
  border-radius: 0.5rem;
  border: 1px solid rgb(229 231 235);
  transition: all 0.2s ease;
}

.social-item:hover {
  background: rgb(239 246 255);
  border-color: rgb(59 130 246);
}

.social-icon {
  color: rgb(59 130 246);
  font-size: 1.125rem;
}

.platform-name {
  font-weight: 600;
  color: rgb(17 24 39);
  min-width: 80px;
  text-transform: capitalize;
}

.platform-url {
  color: rgb(107 114 128);
  font-size: 0.875rem;
  word-break: break-all;
}

/* ====== 现代化操作按钮区域 ====== */
.action-section {
  display: flex;
  gap: 1.5rem;
  justify-content: center;
  padding: 3rem 0;
  margin-top: 3rem;
  position: relative;
}

.action-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg, 
    transparent 0%, 
    rgba(59, 130, 246, 0.3) 25%, 
    rgba(139, 92, 246, 0.3) 75%, 
    transparent 100%
  );
}

.save-button {
  background: linear-gradient(135deg, rgb(34 197 94), rgb(22 163 74));
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 0.75rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgb(34 197 94 / 0.25);
}

.save-button:hover {
  background: linear-gradient(135deg, rgb(22 163 74), rgb(21 128 61));
  transform: translateY(-2px);
  box-shadow: 0 8px 12px rgb(34 197 94 / 0.35);
}

.reset-button {
  background: rgb(249 250 251);
  border: 1px solid rgb(209 213 219);
  color: rgb(75 85 99);
  padding: 0.75rem 2rem;
  border-radius: 0.75rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.reset-button:hover {
  background: rgb(243 244 246);
  border-color: rgb(156 163 175);
  color: rgb(55 65 81);
}

.button-icon {
  margin-right: 0.5rem;
}

/* ====== 状态提示 ====== */
.error-alert,
.success-alert,
.json-error-alert {
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

/* ====== 响应式设计 ====== */
@media (max-width: 768px) {
  .profile-page-container {
    padding: 1rem 0.75rem;
  }
  
  .page-title {
    font-size: 1.875rem;
  }
  
  .page-subtitle {
    font-size: 1rem;
  }
  
  .avatar-section {
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 1.5rem;
  }
  
  .avatar-controls {
    width: 100%;
    gap: 1rem;
  }
  
  .action-section {
    flex-direction: column;
    align-items: stretch;
  }
  
  .save-button,
  .reset-button {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .profile-header {
    padding: 1.5rem 1rem;
  }
  
  .avatar-container {
    width: 80px;
    height: 80px;
  }
  
  .placeholder-icon {
    font-size: 2rem;
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

/* ====== Element Plus 样式深度覆盖 ====== */
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
</style>
