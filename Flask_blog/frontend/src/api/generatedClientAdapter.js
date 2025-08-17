// 兼容 index.js 的 bindGeneratedClient 导出（如需扩展可在此实现）
export function bindGeneratedClient(OpenAPI) {
  // 目前无需特殊处理，保留接口以兼容调用
  return OpenAPI;
}
// 将 openapi-typescript-codegen 生成的 axios 实例与自定义拦截器统一
// 约定: 生成目录在 src/generated
// 此适配器暴露一个初始化方法，用现有 apiClient 的 axios 实例替换生成代码里的默认 axios

import api from '../apiClient';
import { OpenAPI } from '../generated/core/OpenAPI';
import { request as genRequest } from '../generated/core/request';
import { useSessionStore } from '../stores/session';
import router from '../router';

OpenAPI.TOKEN = () => Promise.resolve(localStorage.getItem('access_token') || '');
// Important: generated paths already start with '/api/v1', so BASE must be empty to avoid '/api/v1/api/v1/...'
OpenAPI.BASE = '';

// 简易 ETag 缓存: key = method + url + serialized params
const etagCache = new Map(); // key -> { etag, data, ts }
const ETAG_TTL = 60_000; // 60s

function getSession(){
  try { return useSessionStore(); } catch { return null; }
}

async function refreshTokenOnce(){
  if(refreshTokenOnce._p) return refreshTokenOnce._p; // 单飞
  const refreshUrl = '/api/v1/auth/refresh';
  const prevToken = localStorage.getItem('access_token') || '';
  refreshTokenOnce._p = api.post(refreshUrl, {}, { headers: { Authorization: 'Bearer ' + prevToken }}).then(r=>{
    const token = r.data?.data?.access_token;
    if(token){
      localStorage.setItem('access_token', token);
      const s = getSession(); s && s.setAuth(token, s.role);
    }
    return token;
  }).catch(e=>{ throw e; }).finally(()=>{ setTimeout(()=>{ refreshTokenOnce._p=null; }, 0); });
  return refreshTokenOnce._p;
}
refreshTokenOnce._p = null;

function makeCacheKey(req){
  const { method='GET', url, query } = req;
  const q = query ? JSON.stringify(query) : '';
  return method.toUpperCase() + ' ' + url + ' ' + q;
}

function handleAuthFailure(){
  const s = getSession();
  s && s.logout();
  if(router.currentRoute.value.path !== '/login'){
    router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } });
  }
}

export function clearETagCache(){ etagCache.clear(); }
export function etagCacheStats(){ return { size: etagCache.size }; }

if(typeof window !== 'undefined'){
  window.__API_CACHE__ = { clear: clearETagCache, stats: etagCacheStats, _raw: etagCache };
}

export async function request(options){
  const isGet = (options.method||'get').toLowerCase()==='get';
  const key = isGet ? makeCacheKey(options) : null;
  if(isGet && key && etagCache.has(key)){
    const entry = etagCache.get(key);
    if(Date.now() - entry.ts < ETAG_TTL){
      options.headers = { ...(options.headers||{}), 'If-None-Match': entry.etag };
    } else {
      etagCache.delete(key);
    }
  }
  try {
    const resp = await genRequest(OpenAPI, options, api);
    const etag = resp?.headers?.get ? resp.headers.get('ETag') : resp?.headers?.etag;
    if(isGet && key && etag){
      etagCache.set(key, { etag, data: resp, ts: Date.now() });
    }
    return resp;
  } catch(err){
    if(isGet && key && err?.status===304 && etagCache.has(key)){
      return etagCache.get(key).data;
    }
    const bodyCode = err?.body?.code;
    if(err?.status===401 || bodyCode===2001){
      try {
        await refreshTokenOnce();
        return await genRequest(OpenAPI, options, api);
      } catch(e2){
        handleAuthFailure();
        throw e2;
      }
    }
    throw err;
  }
}

export function createServices(Services){
  const API = { ...Services };

  // Alias: SearchService.search -> generated getApiV1Search
  if(API.SearchService && !API.SearchService.search){
    API.SearchService.search = (opts={})=>{
      const {
        q, page, page_size, status, tag, tags, match_mode,
        category_id, author_id, sort, date_from, date_to, facets
      } = (opts||{});
      return Services.SearchService.getApiV1Search(
        q, page, page_size, status, tag, tags, match_mode,
        category_id, author_id, sort, date_from, date_to, facets
      );
    };
  }

  // Alias: ArticlesService.listArticles -> public list endpoint
  if(API.ArticlesService && !API.ArticlesService.listArticles){
    API.ArticlesService.listArticles = async (opts={})=>{
      const { page, page_size, tag, category_id, author_id, sort } = (opts||{});
      try {
        return await Services.ArticlesService.getApiV1ArticlesPublic(page, page_size, tag, category_id, author_id, sort);
      } catch(e){
        // fallback to legacy public API when generated endpoint not available
        const r = await api.get('/public/v1/articles', { params: { page, page_size, tag, category_id, author_id, sort }, baseURL: '' });
        return r.data;
      }
    };
  }

  // Polyfill: TaxonomyService (categories/tags) with public fallback
  if(!API.TaxonomyService){
    API.TaxonomyService = {
      listCategories: async ()=>{
        try { return await api.get('/categories/'); }
        catch { return await api.get('/public/v1/categories', { baseURL: '' }); }
      },
      listTags: async ()=>{
        try { return await api.get('/tags/'); }
        catch { return await api.get('/public/v1/tags', { baseURL: '' }); }
      },
    };
  }

  // Alias: AuthService methods to simple names
  if(API.AuthService){
    if(!API.AuthService.register){
      API.AuthService.register = ({ requestBody }) => Services.AuthService.postApiV1AuthRegister(requestBody);
    }
    if(!API.AuthService.login){
      API.AuthService.login = ({ requestBody }) => Services.AuthService.postApiV1AuthLogin(requestBody);
    }
  }

  return API;
}
