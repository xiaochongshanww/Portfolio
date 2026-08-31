import axios from 'axios';

// 统一 axios 基础实例
// 注:刷新逻辑需同时存在于 generatedClientAdapter(生成栈)与此处(手写栈),
// 否则手写方法(getAdminComments 等)在 JWT 过期后 401 不重试,
// 页面表现为"已登录但列表加载失败"(2026-08-31 修复)。
const api = axios.create({ baseURL: '/api/v1', withCredentials: true, headers:{ 'Accept':'application/json, text/plain, */*' } });
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token');
  if(token) {
    cfg.headers.Authorization = 'Bearer ' + token;
  }
  // CSRF 双提交：若存在 XSRF-TOKEN Cookie 则写入头
  try {
    const cookies = document.cookie.split(';').map(s=>s.trim());
    const kv = cookies.find(c=>c.startsWith('XSRF-TOKEN='));
    if(kv){
      const val = decodeURIComponent(kv.split('=')[1]);
      cfg.headers['X-XSRF-TOKEN'] = val;
    }
  }catch(_e){ /* ignore */ }
  return cfg;
});

// 401 → 单飞刷新 → 原请求重试一次(与 generatedClientAdapter 同语义)
/** @type {Promise<string> | null} */
let refreshingPromise = null;
api.interceptors.response.use(
  (resp) => resp,
  async (err) => {
    const status = err.response?.status;
    const bodyCode = err.response?.data?.code;
    const original = err.config;
    if ((status === 401 || bodyCode === 2001) && original && !original._retried) {
      original._retried = true;
      if (!refreshingPromise) {
        const prevToken = localStorage.getItem('access_token') || '';
        refreshingPromise = axios
          .post('/api/v1/auth/refresh', {}, { headers: { Authorization: 'Bearer ' + prevToken }, withCredentials: true })
          .then((r) => {
            const token = r.data?.data?.access_token;
            if (token) localStorage.setItem('access_token', token);
            return token;
          })
          .finally(() => { refreshingPromise = null; });
      }
      try {
        const token = await refreshingPromise;
        original.headers.Authorization = 'Bearer ' + token;
        return api(original);
      } catch (_e) {
        // 刷新失败(过期/无效):清 token,让路由守卫/调用方走未认证分支
        localStorage.removeItem('access_token');
        throw err;
      }
    }
    throw err;
  }
);

export default api;
