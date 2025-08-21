<template>
  <div class="auth-page-container">
    <div class="auth-form-wrapper">
      <div class="auth-header">
        <h1 class="auth-title">创建新账户</h1>
        <p class="auth-subtitle">加入我们的社区，开始您的博客之旅</p>
      </div>
      
      <el-card class="auth-card" shadow="always">
        <el-form @submit.prevent="submit" @keyup.enter="submit" label-position="top" class="auth-form">
          <el-form-item label="邮箱地址" class="auth-form-item">
            <el-input 
              v-model="email" 
              type="email" 
              placeholder="you@example.com" 
              size="large" 
              clearable
              class="auth-input"
            />
          </el-form-item>
          
          <el-form-item label="密码" class="auth-form-item">
            <el-input 
              v-model="password" 
              type="password" 
              show-password 
              placeholder="至少 6 位" 
              size="large"
              class="auth-input"
              @keyup.enter="submit"
            />
          </el-form-item>
          
          <el-alert 
            v-if="error" 
            :title="error" 
            type="error" 
            show-icon 
            :closable="false" 
            class="auth-error-alert" 
          />

          <el-form-item class="auth-submit-item">
            <el-button 
              type="primary" 
              :loading="loading" 
              @click="submit" 
              class="auth-submit-btn" 
              size="large"
            >
              注册
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
      
      <p class="auth-footer-text">
        已有账号？
        <RouterLink to="/login" class="auth-link">立即登录</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import apiClient from '../apiClient'; // Simplified API client
import { ElMessage } from 'element-plus';

// Simplified API for demonstration
const API = {
  AuthService: {
    register: (body) => apiClient.post('/auth/register', body.requestBody)
  }
}

const router = useRouter();
const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

async function submit() {
  if (!email.value || !password.value) {
      ElMessage.error('请输入邮箱和密码');
      return;
  }
   if (password.value.length < 6) {
      ElMessage.error('密码长度至少为 6 位');
      return;
  }
  loading.value = true;
  error.value = '';
  try {
    await API.AuthService.register({ requestBody: { email: email.value, password: password.value } });
    ElMessage.success('注册成功！现在您可以登录了。');
    router.push('/login');
  } catch (e) {
    error.value = e.response?.data?.message || '注册失败，邮箱可能已被使用';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
/* 认证页面容器 - 渐进式响应设计 */
.auth-page-container {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgb(239 246 255) 0%, rgb(249 250 251) 50%, rgb(243 244 246) 100%);
  padding: 2rem 1rem;
  position: relative;
}

/* 背景装饰 */
.auth-page-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 25% 25%, rgba(59, 130, 246, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(139, 92, 246, 0.1) 0%, transparent 50%);
  pointer-events: none;
}

/* 表单容器 - 响应式宽度 */
.auth-form-wrapper {
  width: 100%;
  max-width: 420px;
  position: relative;
  z-index: 1;
}

/* 移动端适配 */
@media (min-width: 640px) {
  .auth-form-wrapper {
    max-width: 480px;
  }
}

@media (min-width: 768px) {
  .auth-form-wrapper {
    max-width: 520px;
  }
}

@media (min-width: 1024px) {
  .auth-form-wrapper {
    max-width: 560px;
  }
}

/* 页面头部 */
.auth-header {
  text-align: center;
  margin-bottom: 2rem;
}

.auth-title {
  font-size: 2rem;
  font-weight: 700;
  color: rgb(17 24 39);
  margin-bottom: 0.5rem;
  letter-spacing: -0.025em;
}

.auth-subtitle {
  color: rgb(107 114 128);
  font-size: 1rem;
  margin: 0;
  line-height: 1.5;
}

/* 认证卡片 */
.auth-card {
  border-radius: 1rem;
  border: 1px solid rgb(229 231 235);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 2.5rem;
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}

/* 表单样式 */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.auth-form-item {
  margin-bottom: 0;
}

/* 输入框样式 */
.auth-input :deep(.el-input__wrapper) {
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
  transition: all 0.2s ease;
}

.auth-input :deep(.el-input__wrapper):hover {
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.auth-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgb(59 130 246 / 0.3), 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

/* 错误提示 */
.auth-error-alert {
  border-radius: 0.75rem;
  margin: 1rem 0;
}

/* 提交按钮 */
.auth-submit-item {
  margin-top: 1rem;
  margin-bottom: 0;
}

.auth-submit-btn {
  width: 100%;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.2s ease;
  background: linear-gradient(135deg, rgb(59 130 246), rgb(37 99 235));
  border: none;
}

.auth-submit-btn:hover {
  background: linear-gradient(135deg, rgb(37 99 235), rgb(29 78 216));
  transform: translateY(-1px);
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}

/* 底部文本 */
.auth-footer-text {
  text-align: center;
  margin-top: 1.5rem;
  color: rgb(107 114 128);
  font-size: 0.875rem;
}

.auth-link {
  color: rgb(59 130 246);
  font-weight: 600;
  text-decoration: none;
  transition: color 0.2s ease;
}

.auth-link:hover {
  color: rgb(37 99 235);
  text-decoration: underline;
}

/* 移动端优化 */
@media (max-width: 640px) {
  .auth-page-container {
    padding: 1rem 0.75rem;
  }
  
  .auth-card {
    padding: 1.5rem;
  }
  
  .auth-title {
    font-size: 1.75rem;
  }
  
  .auth-subtitle {
    font-size: 0.875rem;
  }
}
</style>