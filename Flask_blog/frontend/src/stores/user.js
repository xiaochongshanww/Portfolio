import { defineStore } from 'pinia';
import apiClient from '../apiClient';

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    role: localStorage.getItem('role') || '',
    user: null,
    isAuthenticated: false
  }),
  
  getters: {
    hasRole: (state) => (roles) => {
      if (!Array.isArray(roles)) roles = [roles];
      return state.user && roles.includes(state.user.role);
    },
    
    isAdmin: (state) => state.user?.role === 'admin',
    isEditor: (state) => state.user?.role === 'editor',
    isAuthor: (state) => state.user?.role === 'author',
    
    canAccessAdmin: (state) => {
      return state.user && ['admin', 'editor', 'author'].includes(state.user.role);
    },
    
    canManageUsers: (state) => state.user?.role === 'admin',
    canModerateContent: (state) => state.user && ['admin', 'editor'].includes(state.user.role)
  },
  
  actions: {
    setAuth(token, role) {
      this.token = token; 
      this.role = role;
      this.isAuthenticated = !!token;
      localStorage.setItem('access_token', token);
      localStorage.setItem('role', role || '');
    },
    
    async fetchUserInfo() {
      if (!this.token) {
        this.user = null;
        this.isAuthenticated = false;
        return null;
      }
      
      try {
        const response = await apiClient.get('/users/me');
        this.user = response.data.data;
        this.isAuthenticated = true;
        // 同步角色信息
        if (this.user.role !== this.role) {
          this.role = this.user.role;
          localStorage.setItem('role', this.user.role);
        }
        return this.user;
      } catch (error) {
        console.error('获取用户信息失败:', error);
        // 如果token无效，清除认证信息
        if (error.response?.status === 401) {
          this.logout();
        }
        return null;
      }
    },
    
    async login(token, role) {
      this.setAuth(token, role);
      await this.fetchUserInfo();
    },
    
    async logout() {
      try {
        // 调用后端退出登录接口
        await apiClient.post('/auth/logout');
      } catch (error) {
        console.error('后端退出登录失败:', error);
        // 即使后端调用失败，也继续清除前端状态
      }
      
      // 清除前端状态
      this.token = ''; 
      this.role = ''; 
      this.user = null;
      this.isAuthenticated = false;
      localStorage.removeItem('access_token');
      localStorage.removeItem('role');
    },
    
    // 初始化认证状态
    async initAuth() {
      console.log('🔐 初始化认证状态...');
      console.log('🔐 当前token:', this.token ? '已存在' : '不存在');
      console.log('🔐 localStorage中的token:', localStorage.getItem('access_token') ? '已存在' : '不存在');
      
      if (this.token) {
        console.log('🔐 开始获取用户信息...');
        await this.fetchUserInfo();
        console.log('🔐 用户信息获取完成，认证状态:', this.isAuthenticated);
        console.log('🔐 用户信息:', this.user);
      } else {
        console.log('🔐 无token，跳过用户信息获取');
      }
    },
    
    // 强制重新加载用户信息
    async refreshUserInfo() {
      console.log('🔄 强制刷新用户信息...');
      this.user = null;
      await this.fetchUserInfo();
    }
  }
});