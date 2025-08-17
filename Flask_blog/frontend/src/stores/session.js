import { defineStore } from 'pinia';
import apiClient from '../apiClient';

export const useSessionStore = defineStore('session', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    role: localStorage.getItem('role') || '',
    user: null
  }),
  actions: {
    setAuth(token, role){
      this.token = token; 
      this.role = role;
      localStorage.setItem('access_token', token);
      localStorage.setItem('role', role || '');
    },
    
    async fetchUserInfo(){
      if (!this.token) {
        this.user = null;
        return null;
      }
      try {
        const response = await apiClient.get('/users/me');
        this.user = response.data.data;
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
    
    async logout(){
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
      localStorage.removeItem('access_token');
      localStorage.removeItem('role');
    }
  }
});
