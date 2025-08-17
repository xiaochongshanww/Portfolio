<template>
  <div class="min-h-[70vh] flex flex-col items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="w-full max-w-md space-y-8">
      <div>
        <h1 class="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">登录您的账户</h1>
      </div>
      <el-card class="p-5">
        <el-form @submit.prevent label-position="top" class="space-y-6">
          <el-form-item label="邮箱地址">
            <el-input v-model="email" type="email" placeholder="you@example.com" size="large" clearable />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="password" type="password" show-password placeholder="输入密码" size="large" />
          </el-form-item>
          
          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="!mb-4" />

          <el-form-item class="!mt-8">
            <el-button type="primary" :loading="loading" @click="submit" class="w-full" size="large">登录</el-button>
          </el-form-item>
        </el-form>
      </el-card>
      <p class="mt-4 text-center text-sm text-gray-600">
        没有账号？
        <RouterLink to="/register" class="font-medium text-blue-600 hover:text-blue-500">立即注册</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useSessionStore } from '../stores/session';
import apiClient from '../apiClient'; // Simplified API client
import { ElMessage } from 'element-plus';

// Simplified API for demonstration
const API = {
  AuthService: {
    login: (body) => apiClient.post('/auth/login', body.requestBody)
  }
}

const router = useRouter();
const session = useSessionStore();
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
    await session.login(resp.data.data.access_token, resp.data.data.role);
    ElMessage.success('登录成功');
    router.push('/');
  } catch (e) {
    error.value = e.response?.data?.message || '登录失败，请检查您的凭据';
  } finally {
    loading.value = false;
  }
}
</script>