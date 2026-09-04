<template>
  <div class="profile-page">
    <!-- 页头 -->
    <section class="page-head">
      <div class="eyebrow">设置</div>
      <h1>个人中心</h1>
      <p>管理你的个人资料与账户安全。</p>
    </section>

    <!-- 加载状态 -->
    <div v-if="!loaded" class="page-loading">加载中...</div>

    <!-- 05 §23 Settings Pattern:Stacked Sections -->
    <div v-else class="settings-stack">
      <!-- 基本资料 -->
      <section class="card">
        <div class="card-head">
          <h2>基本资料</h2>
          <div class="head-actions">
            <el-button size="small" :disabled="saving" @click="resetForm">重置</el-button>
            <el-button type="primary" size="small" :loading="saving" @click="save">保存更改</el-button>
          </div>
        </div>
        <div class="card-body">
          <el-alert
            v-if="error"
            :title="error"
            type="error"
            class="card-alert"
            @close="error = ''"
          />
          <el-alert
            v-if="saved"
            title="个人资料已保存"
            type="success"
            class="card-alert"
            @close="saved = false"
          />

          <!-- 头像 -->
          <div class="avatar-row">
            <div class="avatar-box">
              <img
                v-if="form.avatar && !avatarError"
                :src="form.avatar"
                alt="头像预览"
                @error="handleAvatarError"
                @load="handleAvatarLoad"
              >
              <div v-else class="avatar-fallback">
                <el-icon :size="26"><User /></el-icon>
              </div>
            </div>
            <div class="avatar-main">
              <div class="avatar-status">
                <span v-if="form.avatar">
                  <span v-if="avatarLoading">检测中...</span>
                  <span v-else-if="avatarError" class="status-error">头像加载失败</span>
                  <span v-else class="status-ok">头像正常</span>
                </span>
                <span v-else>尚未设置头像</span>
              </div>
              <div class="avatar-actions">
                <el-upload
                  action="#"
                  :auto-upload="false"
                  :on-change="handleFileSelect"
                  :show-file-list="false"
                  accept="image/*"
                  :disabled="uploading"
                >
                  <el-button size="small" type="primary" :loading="uploading">
                    {{ uploading ? '上传中...' : '上传头像' }}
                  </el-button>
                </el-upload>
              </div>
              <p class="hint">支持 JPG、PNG、WebP,不超过 5MB,建议尺寸 200×200。</p>
              <el-progress
                v-if="uploading"
                :percentage="uploadProgress"
                class="upload-progress"
              />
            </div>
          </div>

          <el-collapse class="url-collapse">
            <el-collapse-item title="使用图片链接" name="url">
              <el-input
                v-model="form.avatar"
                placeholder="https://example.com/avatar.jpg"
                clearable
              />
              <p class="hint">直接填写头像图片的网络地址,保存后生效。</p>
            </el-collapse-item>
          </el-collapse>

          <el-form label-position="top" class="settings-form">
            <div class="form-grid">
              <el-form-item label="昵称">
                <el-input
                  v-model="form.nickname"
                  maxlength="80"
                  placeholder="请输入您的昵称"
                  show-word-limit
                  clearable
                />
              </el-form-item>
              <el-form-item label="显示效果预览">
                <div class="preview-name">{{ getDisplayPreview() }}</div>
                <p class="hint">其他用户看到的名称,将出现在文章和评论中。</p>
              </el-form-item>
            </div>
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
            </el-form-item>
            <el-form-item label="社交链接(JSON)">
              <el-input
                v-model="form.social_links_raw"
                type="textarea"
                :rows="5"
                class="json-input"
                :placeholder="socialPlaceholder"
              />
              <p class="hint">支持 GitHub、Twitter、LinkedIn、微信等平台,使用 JSON 对象格式。</p>
            </el-form-item>
          </el-form>

          <!-- 社交链接预览 -->
          <div v-if="parsedSocialLinks" class="social-preview">
            <div
              v-for="(url, platform) in parsedSocialLinks"
              :key="platform"
              class="social-item"
            >
              <span class="platform">{{ platform }}</span>
              <span class="url">{{ url }}</span>
            </div>
          </div>

          <el-alert
            v-if="socialLinksError"
            :title="socialLinksError"
            type="warning"
            :closable="false"
            class="card-alert"
          />
        </div>
      </section>

      <!-- 账户安全 -->
      <section class="card">
        <div class="card-head">
          <h2>账户安全</h2>
        </div>
        <div class="card-body">
          <el-alert
            v-if="passwordError"
            :title="passwordError"
            type="error"
            class="card-alert"
            @close="passwordError = ''"
          />
          <el-alert
            v-if="passwordChanged"
            title="密码修改成功"
            description="请使用新密码重新登录。"
            type="success"
            class="card-alert"
            @close="passwordChanged = false"
          />

          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-position="top"
            class="settings-form"
          >
            <div class="form-grid">
              <el-form-item label="当前密码" prop="currentPassword">
                <el-input
                  v-model="passwordForm.currentPassword"
                  type="password"
                  placeholder="请输入当前密码"
                  clearable
                  show-password
                />
              </el-form-item>
              <el-form-item label="新密码" prop="newPassword">
                <el-input
                  v-model="passwordForm.newPassword"
                  type="password"
                  placeholder="至少 8 位,含字母和数字"
                  clearable
                  show-password
                />
              </el-form-item>
            </div>
            <div class="form-grid">
              <el-form-item label="确认新密码" prop="confirmPassword">
                <el-input
                  v-model="passwordForm.confirmPassword"
                  type="password"
                  placeholder="请再次输入新密码"
                  clearable
                  show-password
                />
              </el-form-item>
            </div>

            <!-- 密码强度 -->
            <div v-if="passwordForm.newPassword" class="password-strength">
              <span class="strength-label">密码强度</span>
              <div class="strength-bar">
                <div
                  class="strength-fill"
                  :class="passwordStrengthClass"
                  :style="{ width: passwordStrengthPercent + '%' }"
                />
              </div>
              <span class="strength-text" :class="passwordStrengthClass">
                {{ passwordStrengthText }}
              </span>
            </div>

            <div class="form-actions">
              <el-button
                type="primary"
                :loading="changingPassword"
                @click="changePassword"
              >
                {{ changingPassword ? '修改中...' : '修改密码' }}
              </el-button>
              <el-button :disabled="changingPassword" @click="resetPasswordForm">清空</el-button>
            </div>
          </el-form>
          <p class="hint">修改成功后将自动退出登录,请使用新密码重新登录。</p>
        </div>
      </section>
    </div>
  </div>
</template>
<script setup>
/**
 * 个人中心(V2 重构,原型 profile-v1;05 §23 Settings Sections)
 * 两个 Section:基本资料(头像/昵称/简介/社交链接,单一保存动作)+ 账户安全(修改密码)。
 * 数据流保持原状:UsersService.get/patchApiV1UsersMe、UploadsService.postApiV1UploadsImage、
 * API.changePassword(成功后 3 秒登出)。
 */
import { ref, computed, onMounted } from 'vue';
import { UsersService, UploadsService } from '../generated';
import { API } from '../api';
import { useNotify } from '../composables/useNotify';
import { setMeta } from '../composables/useMeta';
import { getUserDisplayName } from '../utils/userDisplay';
import { ElMessage } from 'element-plus';
import { useUserStore } from '../stores/user';

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
/** @type {import('vue').Ref<{ nickname: string; bio: string; avatar: string; social_links_raw: string }>} */
const originalForm = ref({ nickname: '', bio: '', avatar: '', social_links_raw: '' });

// 密码修改相关状态
const changingPassword = ref(false);
const passwordChanged = ref(false);
const passwordError = ref('');
/** @type {import('vue').Ref<{ validate: () => Promise<boolean>; clearValidate: () => void } | null>} */
const passwordFormRef = ref(null);

// 密码表单数据
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
});

const socialPlaceholder = JSON.stringify(
  { github: 'https://github.com/username', twitter: 'https://twitter.com/username' },
  null,
  2,
);

// 密码验证规则
const passwordRules = {
  currentPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
    { validator: validateNewPassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
};

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
    const err = /** @type {{ message?: string }} */ (e);
    return `JSON 格式错误: ${err.message}`;
  }
});

// 密码强度计算
const passwordStrength = computed(() => {
  const password = passwordForm.value.newPassword;
  if (!password) return 0;

  let score = 0;

  // 长度检查
  if (password.length >= 8) score += 25;
  if (password.length >= 12) score += 25;

  // 包含小写字母
  if (/[a-z]/.test(password)) score += 15;

  // 包含大写字母
  if (/[A-Z]/.test(password)) score += 15;

  // 包含数字
  if (/\d/.test(password)) score += 10;

  // 包含特殊字符
  if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) score += 10;

  return Math.min(score, 100);
});

const passwordStrengthPercent = computed(() => passwordStrength.value);

const passwordStrengthClass = computed(() => {
  const strength = passwordStrength.value;
  if (strength < 30) return 'strength-weak';
  if (strength < 60) return 'strength-medium';
  if (strength < 80) return 'strength-good';
  return 'strength-strong';
});

const passwordStrengthText = computed(() => {
  const strength = passwordStrength.value;
  if (strength < 30) return '弱';
  if (strength < 60) return '中等';
  if (strength < 80) return '良好';
  return '强';
});

// 加载用户数据
async function load() {
  try {
    const r = await UsersService.getApiV1UsersMe();
    const d = r.data;

    form.value.nickname = d?.nickname || '';
    form.value.bio = d?.bio || '';
    form.value.avatar = d?.avatar || '';

    if (d?.social_links) {
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
    // 提取详细错误信息
    const err = /** @type {{ response?: { data?: { message?: string, data?: unknown } }, message?: string }} */ (e);
    if (err.response?.data) {
      const errorData = err.response.data;
      if (errorData.message) {
        error.value = errorData.message;
        // 如果有具体的验证错误信息，也显示出来
        if (errorData.data && typeof errorData.data === 'string') {
          error.value += `: ${errorData.data}`;
        }
      } else {
        error.value = '保存失败，请检查输入信息';
      }
    } else if (err.message) {
      error.value = `保存失败: ${err.message}`;
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
/** @param {{ raw?: File }} file */
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
        ElMessage.warning('头像上传成功，但自动保存失败，请手动点击保存按钮');
      }
    } else {
      error.value = '上传成功但未获取到图片地址';
    }
  } catch (e) {
    const err = /** @type {{ response?: { data?: { message?: string } } }} */ (e);
    if (err.response?.data?.message) {
      error.value = `上传失败: ${err.response.data.message}`;
    } else {
      error.value = '头像上传失败，请稍后重试';
    }
  } finally {
    uploading.value = false;
    uploadProgress.value = 0;
  }
}

// 密码验证函数
/**
 * @param {unknown} rule
 * @param {string | undefined} value
 * @param {(err?: Error) => void} callback
 */
function validateNewPassword(rule, value, callback) {
  if (!value) {
    callback(new Error('请输入新密码'));
    return;
  }

  if (value.length < 8) {
    callback(new Error('密码长度至少8位'));
    return;
  }

  // 检查密码复杂度
  const hasLetter = /[a-zA-Z]/.test(value);
  const hasNumber = /\d/.test(value);

  if (!hasLetter || !hasNumber) {
    callback(new Error('密码应包含字母和数字'));
    return;
  }

  // 检查与当前密码是否相同
  if (value === passwordForm.value.currentPassword) {
    callback(new Error('新密码不能与当前密码相同'));
    return;
  }

  callback();
}

/**
 * @param {unknown} rule
 * @param {string | undefined} value
 * @param {(err?: Error) => void} callback
 */
function validateConfirmPassword(rule, value, callback) {
  if (!value) {
    callback(new Error('请确认新密码'));
    return;
  }

  if (value !== passwordForm.value.newPassword) {
    callback(new Error('两次输入的密码不一致'));
    return;
  }

  callback();
}

// 密码修改
async function changePassword() {
  if (!passwordFormRef.value) return;

  try {
    // 表单验证
    const valid = await passwordFormRef.value.validate();
    if (!valid) return;
  } catch (error) {
    return;
  }

  changingPassword.value = true;
  passwordError.value = '';
  passwordChanged.value = false;

  try {
    // 获取用户邮箱
    const userInfo = await UsersService.getApiV1UsersMe();
    const userEmail = userInfo.data?.email;

    if (!userEmail) {
      passwordError.value = '无法获取用户邮箱信息';
      return;
    }

    // 调用密码修改API
    const response = await API.changePassword({
      email: userEmail,
      old_password: passwordForm.value.currentPassword,
      new_password: passwordForm.value.newPassword
    });

    const respData = response.data || {}
    if (response.status >= 400 || respData.code !== 0) {
      // 处理HTTP错误状态
      let errorMessage = '密码修改失败';
      try {
        errorMessage = respData.message || `HTTP ${response.status}: ${response.statusText}`;
      } catch (e) {
        errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      }
      passwordError.value = errorMessage;
      return;
    }

    const result = response.data;

    if (result.code === 0) {
      passwordChanged.value = true;
      resetPasswordForm();

      // 3秒后自动登出，要求用新密码重新登录
      setTimeout(() => {
        ElMessage.info('请使用新密码重新登录');
        userStore.logout();
      }, 3000);

    } else {
      passwordError.value = result.message || '密码修改失败';
    }
  } catch (error) {
    const err = /** @type {{ response?: { data?: { message?: string } } }} */ (error);
    if (err.response?.data) {
      const errorData = err.response.data;
      passwordError.value = errorData.message || '密码修改失败';
    } else {
      passwordError.value = '网络错误，请稍后重试';
    }
  } finally {
    changingPassword.value = false;
  }
}

// 重置密码表单
function resetPasswordForm() {
  passwordForm.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  };

  if (passwordFormRef.value) {
    passwordFormRef.value.clearValidate();
  }

  passwordError.value = '';
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
    title: '个人中心',
    description: '管理你的个人资料与账户安全'
  });
  load();
});
</script>
<style scoped>
.page-head {
  padding-bottom: 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.page-head h1 {
  margin: 0;
  font-size: 26px;
  letter-spacing: -0.04em;
  color: var(--text);
}
.page-head p {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--muted);
}
.page-loading {
  padding: 48px 0;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

/* Settings Sections(05 §23) */
.settings-stack {
  display: grid;
  gap: 16px;
  max-width: 860px;
}
.card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
  overflow: hidden; /* 裁掉卡头背景的方角 */
}
.card-head {
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.card-head h2 {
  font-size: 14px;
  margin: 0;
  color: var(--text);
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-body {
  padding: 16px;
}
.card-alert {
  margin-bottom: 14px;
}

/* 头像 */
.avatar-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  padding-bottom: 16px;
}
.avatar-box {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--surface-2);
  flex-shrink: 0;
}
.avatar-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.avatar-fallback {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--muted);
}
.avatar-main {
  min-width: 0;
}
.avatar-status {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 8px;
}
.status-ok {
  color: var(--green-ink);
}
.status-error {
  color: #b91c1c;
}
.avatar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.upload-progress {
  width: 240px;
  max-width: 100%;
  margin-top: 10px;
}
.url-collapse {
  margin-bottom: 16px;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

/* 表单 */
.settings-form :deep(.el-form-item) {
  margin-bottom: 14px;
}
.settings-form :deep(.el-form-item__label) {
  font-size: 12px;
  color: var(--muted);
  padding-bottom: 4px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 24px;
}
.hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--muted);
}
.preview-name {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-2);
  padding: 7px 12px;
  font-size: 13px;
  color: var(--text);
}
.json-input :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}

/* 社交链接预览 */
.social-preview {
  border-top: 1px solid var(--line);
  padding-top: 4px;
}
.social-item {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 14px;
  padding: 9px 0;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
  align-items: center;
}
.social-item:last-child {
  border-bottom: 0;
}
.social-item .platform {
  color: var(--muted);
}
.social-item .url {
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 密码强度 */
.password-strength {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0 12px;
}
.strength-label {
  font-size: 12px;
  color: var(--muted);
}
.strength-bar {
  flex: 1;
  max-width: 240px;
  height: 6px;
  border-radius: 999px;
  background: var(--surface-2);
  overflow: hidden;
}
.strength-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 180ms ease;
}
.strength-text {
  font-size: 12px;
  font-weight: 650;
}
.strength-weak .strength-fill { background: #dc2626; }
.strength-weak.strength-text { color: #b91c1c; }
.strength-medium .strength-fill { background: #d97706; }
.strength-medium.strength-text { color: #b45309; }
.strength-good .strength-fill { background: #2563eb; }
.strength-good.strength-text { color: #1d4ed8; }
.strength-strong .strength-fill { background: #16a34a; }
.strength-strong.strength-text { color: #15803d; }

.form-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .avatar-row {
    flex-direction: column;
  }
}
</style>
