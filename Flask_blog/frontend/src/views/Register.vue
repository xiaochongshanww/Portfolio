<template>
  <div class="min-h-[70vh] flex flex-col items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="w-full max-w-md space-y-8">
      <div>
        <h1 class="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">创建新账户</h1>
      </div>
      <el-card class="p-5">
        <el-form @submit.prevent label-position="top" class="space-y-6">
          <el-form-item label="邮箱地址">
            <el-input v-model="email" type="email" placeholder="you@example.com" size="large" clearable />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="password" type="password" show-password placeholder="至少 6 位" size="large" />
          </el-form-item>

          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="!mb-4" />

          <el-form-item class="!mt-8">
            <el-button type="primary" :loading="loading" @click="submit" class="w-full" size="large">注册</el-button>
          </el-form-item>
        </el-form>
      </el-card>
      <p class="mt-4 text-center text-sm text-gray-600">
        已有账号？
        <RouterLink to="/login" class="font-medium text-blue-600 hover:text-blue-500">立即登录</RouterLink>
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