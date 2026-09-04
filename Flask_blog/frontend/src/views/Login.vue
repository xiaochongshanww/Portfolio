<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-brand">
        <span class="brand-mark">山</span>
        <span class="brand-name">小重山</span>
      </div>
      <h1 class="auth-title">登录您的账户</h1>
      <p class="auth-subtitle">欢迎回来！请登录您的账户以继续</p>
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
              placeholder="输入密码" 
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
              登录
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
      
      <p class="auth-footer-text">
        没有账号？
        <RouterLink to="/register" class="auth-link">立即注册</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../stores/user';
import { API as UnifiedAPI } from '../api';
import { ElMessage } from 'element-plus';

// Simplified API for demonstration
const API = {
  AuthService: {
    /** @param {{ requestBody: { email: string; password: string } }} body */
    login: (body) => UnifiedAPI.login(body.requestBody)
  }
}

const router = useRouter();
const userStore = useUserStore();
const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

async function submit() {
  if (!email.value || !password.value) {
      ElMessage.error('请输入邮箱和密码');
      return;
  }
  loading.value = true;
  error.value = '';
  try {
    const resp = await API.AuthService.login({ requestBody: { email: email.value, password: password.value } });
    // 使用新的 login 方法，会自动获取用户信息
    await userStore.login(resp.data.data.access_token, resp.data.data.role);
    
    // 停止加载状态，显示成功状态
    loading.value = false;
    
    // 创建一个标记来控制MessageBox的关闭
    let shouldAllowClose = false;
    
    // 使用 MessageBox 显示登录成功确认，但不等待它
    const messageBoxPromise = ElMessageBox({
      title: '🎉 登录成功',
      message: `
        <div style="text-align: center; padding: 20px 0;">
          <div style="font-size: 48px; margin-bottom: 16px;">✨</div>
          <div style="font-size: 18px; font-weight: 600; color: #059669; margin-bottom: 8px;">
            欢迎回来！
          </div>
          <div style="font-size: 14px; color: #6b7280; margin-bottom: 16px;">
            正在为您跳转到主页...
          </div>
          <div style="width: 200px; height: 4px; background: #f3f4f6; border-radius: 2px; margin: 0 auto; overflow: hidden;">
            <div style="width: 100%; height: 100%; background: #f1f5f9; border-radius: 2px; animation: progressBar 2s ease-in-out;"></div>
          </div>
        </div>
      `,
      dangerouslyUseHTMLString: true,
      showCancelButton: false,
      showConfirmButton: false,
      showClose: false,
      center: true,
      customClass: 'login-success-dialog',
      beforeClose: (action, instance, done) => {
        // 只有当允许关闭时才关闭
        if (shouldAllowClose) {
          done();
        } else {
          // 阻止用户手动关闭
          return false;
        }
      }
    }).catch(() => {
      // 捕获关闭时的rejected promise
      console.log('MessageBox已关闭');
    });
    
    // 2秒后自动关闭对话框并跳转
    setTimeout(() => {
      console.log('✅ 用户登录成功，开始跳转到主页');
      
      // 允许关闭MessageBox
      shouldAllowClose = true;
      
      // 关闭所有MessageBox实例
      ElMessageBox.close();
      
      // 跳转到主页
      router.push({ path: '/', query: { _refresh: Date.now() } });
    }, 2000);
  } catch (e) {
    const err = /** @type {{ response?: { data?: { message?: string } } }} */ (e);
    error.value = err.response?.data?.message || '登录失败，请检查您的凭据';
    loading.value = false; // 只有出错时立即停止loading
  }
}
</script>

<style scoped>
/* 登录页(V2 视觉):居中卡 + 品牌标识,公开站 token */
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
.auth-link:hover {
  text-decoration: underline;
}
</style>
