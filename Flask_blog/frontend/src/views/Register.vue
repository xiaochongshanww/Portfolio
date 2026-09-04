<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-brand">
        <span class="brand-mark">山</span>
        <span class="brand-name">小重山</span>
      </div>
      <h1 class="auth-title">创建新账户</h1>
      <p class="auth-subtitle">加入我们的社区，开始您的博客之旅</p>
    </div>
    <div class="auth-form-wrapper">
      <el-card class="auth-card" shadow="always">
        <el-form label-position="top" class="auth-form" @submit.prevent="submit" @keyup.enter="submit">
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
              class="auth-submit-btn" 
              size="large" 
              @click="submit"
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
import { API as UnifiedAPI } from '../api';
import { ElMessage } from 'element-plus';

// Simplified API for demonstration
const API = {
  AuthService: {
    /** @param {{ requestBody: { email: string; password: string } }} body */
    register: (body) => UnifiedAPI.register(body.requestBody)
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
    const err = /** @type {{ response?: { data?: { message?: string } } }} */ (e);
    error.value = err.response?.data?.message || '注册失败，邮箱可能已被使用';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 24px;
}
.auth-card {
  width: 100%;
  max-width: 400px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 32px 28px;
}
.auth-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 24px;
}
.brand-mark {
  width: 29px;
  height: 29px;
  border-radius: 8px;
  background: var(--text);
  color: var(--bg);
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
}
.brand-name {
  font-weight: 750;
  font-size: 15px;
  letter-spacing: -0.02em;
  color: var(--text);
}
.auth-title {
  margin: 0 0 6px;
  font-size: 24px;
  letter-spacing: -0.03em;
  color: var(--text);
}
.auth-subtitle {
  margin: 0 0 22px;
  font-size: 14px;
  color: var(--muted);
}
.auth-form :deep(.el-form-item__label) {
  color: var(--muted);
}
.auth-form :deep(.el-input__wrapper) {
  border-radius: 10px;
}
.auth-form :deep(.el-button--primary) {
  width: 100%;
  height: 40px;
  border-radius: 10px;
  font-weight: 650;
}
.auth-footer-text {
  text-align: center;
  margin-top: 18px;
  font-size: 13px;
  color: var(--muted);
}
.auth-link {
  color: var(--primary);
  font-weight: 600;
  text-decoration: none;
}
</style>
