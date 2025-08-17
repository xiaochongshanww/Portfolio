import axios from 'axios';

// 统一 axios 基础实例；刷新逻辑已迁移到 generatedClientAdapter.request 内部，避免双重实现
const api = axios.create({ baseURL: '/api/v1' });
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token');
  if(token) cfg.headers.Authorization = 'Bearer ' + token;
  // CSRF 双提交：若存在 XSRF-TOKEN Cookie 则写入头
  try {
    const cookies = document.cookie.split(';').map(s=>s.trim());
    const kv = cookies.find(c=>c.startsWith('XSRF-TOKEN='));
    if(kv){
      const val = decodeURIComponent(kv.split('=')[1]);
      cfg.headers['X-XSRF-TOKEN'] = val;
    }
  }catch(e){ /* ignore */ }
  return cfg;
});

export default api;
