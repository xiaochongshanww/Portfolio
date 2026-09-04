<template>
  <div v-if="loaded" class="author-page">
    <section class="page-head">
      <div class="eyebrow">作者</div>
      <h1>{{ profile.nickname || ('作者 #' + profile.id) }}</h1>
      <p v-if="profile.bio">{{ profile.bio }}</p>
      <div class="meta">
        <span>{{ total }} 篇文章</span>
        <span v-if="statsLoaded && stats.articles_count != null">· {{ stats.articles_count }} 篇发布</span>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>发布文章</h2>
        <span class="meta">按发布时间排序</span>
      </div>

      <AdminStateBlock
        v-if="!articles.length"
        kind="empty"
        title="暂无文章"
        description="该作者还没有发布任何文章。"
        compact
      />
      <div v-else class="list">
        <div v-for="a in articles" :key="a.id" class="row">
          <time>{{ formatDate(a.published_at || a.created_at) }}</time>
          <div>
            <RouterLink :to="'/article/' + a.slug" class="row-title">{{ a.title }}</RouterLink>
            <small v-if="articleCategoryName(a)" class="row-sub">{{ articleCategoryName(a) }}</small>
          </div>
          <span class="arrow">→</span>
        </div>
      </div>

      <div v-if="total > pageSize" class="pager">
        <button type="button" class="ghost-btn" :disabled="page === 1" @click="prev">‹ 上一页</button>
        <span class="pager-info">{{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }}</span>
        <button type="button" class="ghost-btn" :disabled="page * pageSize >= total" @click="next">下一页 ›</button>
      </div>
    </section>
  </div>
  <div v-else class="author-page"><div class="loading">加载中...</div></div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useNotify } from '../composables/useNotify';
import { UsersService } from '../generated';
import { API } from '../api';
import type { UserPublic } from '../generated';
import type { Article } from '@/types';
import { setMeta, injectJsonLd } from '../composables/useMeta';
import { 
  User, Document, View, Star, Clock, Collection, ArrowRight, Calendar, 
  Folder, ArrowLeft 
} from '@element-plus/icons-vue';

const route = useRoute();
const { pushError } = useNotify();

const props = withDefaults(defineProps<{ id?: string|number }>(), { id: "" })
const userId = computed(() => Number(props.id || route.params.id));
const profile = ref<Partial<UserPublic>>({});
const articles = ref<Article[]>([]);
const stats = ref({ articles_count:0,total_views:0,total_likes:0,last_published_at:null });
const statsLoaded = ref(false);
const loaded = ref(false);
const page = ref(1);
const pageSize = 10;
const total = ref(0);

async function loadProfile(){
  try {
    const r = await UsersService.getApiV1UsersPublic(userId.value);
    profile.value = (r.data || r) as Partial<UserPublic>; // 兼容包装
  } catch(e){ pushError('作者信息获取失败'); }
}
async function loadStats(){
  try {
    const r = await API.getPublicUserStats(userId.value);
    const j = r.data;
    if(j && j.data) stats.value = j.data; statsLoaded.value=true;
  }catch(e){ statsLoaded.value=true; }
}
async function loadArticles(){
  try {
    const r = await UsersService.getApiV1UsersPublicArticles(userId.value, page.value, pageSize, '-published_at');
    const data = r.data;
    // data 可能是 ArticleListResponse
    articles.value = (data?.list || []) as unknown as Article[];
    total.value = data?.total || articles.value.length;
  } catch(e){ pushError('作者文章列表获取失败'); }
}
async function load(){
  loaded.value=false;
  await Promise.all([loadProfile(), loadArticles(), loadStats()]);
  const totalPages = Math.max(1, Math.ceil(total.value / pageSize));
  const prevUrl = page.value>1 ? buildPageUrl(page.value-1) : undefined;
  const nextUrl = page.value< totalPages ? buildPageUrl(page.value+1) : undefined;
  const url = buildPageUrl(page.value);
  setMeta({
    title: (profile.value.nickname || ('作者 #' + (profile.value.id||''))) + ' - 作者主页',
    description: profile.value.bio || '作者主页',
    image: profile.value.avatar,
    prevUrl,
    nextUrl,
    url
  });
  injectJsonLd({ '@context':'https://schema.org', '@type':'ProfilePage', name: profile.value.nickname || ('作者 #' + profile.value.id), url, mainEntity:{ '@type':'Person', name: profile.value.nickname || ('作者 #' + profile.value.id), description: profile.value.bio || undefined, image: profile.value.avatar || undefined }, mainEntityOfPage:{ '@type':'ItemList', itemListElement: articles.value.map((a,i)=>({ '@type':'ListItem', position:i+1, url: window.location.origin + '/article/' + a.slug, name:a.title })) }});
  loaded.value=true;
}
function articleCategoryName(article: Article): string {
  const cat = article.category;
  if (!cat) return '';
  return typeof cat === 'string' ? cat : (cat.name || '');
}
function formatDate(dt: string | null | undefined){ if(!dt) return ''; return new Date(dt).toLocaleDateString(); }
function prev(){ if(page.value>1){ page.value--; loadArticles(); } }
function next(){ if(page.value*pageSize < total.value){ page.value++; loadArticles(); } }
function buildPageUrl(p: number){ const u=new URL(window.location.href); u.searchParams.set('page', String(p)); return u.toString(); }

onMounted(load);
watch(()=>route.params.id, ()=>{ page.value=1; load(); });
</script>
<style scoped>
/* ===== 现代化作者主页样式 ===== */
.modern-author-profile {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem 1rem;
  background: 
#f8fafc;
  min-height: 100vh;
  position: relative;
}

/* 现代化作者头部 */
.modern-author-header {
  position: relative;
  margin-bottom: 3rem;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 2rem;
  padding: 2.5rem;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.06),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
  overflow: hidden;
  transition: all 0.3s ease;
}

.modern-author-header:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 40px rgba(59, 130, 246, 0.08),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
}

.header-decoration {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: #f1f5f9;
  opacity: 0.6;
}

.header-content {
  display: flex;
  gap: 2rem;
  align-items: center;
}

.avatar-section {
  position: relative;
}

.avatar-container {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.modern-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.avatar-container:hover .modern-avatar {
  transform: scale(1.05);
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.avatar-ring {
  position: absolute;
  top: -8px;
  left: -8px;
  right: -8px;
  bottom: -8px;
  border: 3px solid transparent;
  border-radius: 50%;
  background: #3b82f6;
  mask-composite: xor;
  opacity: 0;
  animation: pulse-ring 3s ease-in-out infinite;
}

@keyframes pulse-ring {
  0%, 100% { opacity: 0; transform: scale(0.95); }
  50% { opacity: 0.7; transform: scale(1.05); }
}

.author-meta {
  flex: 1;
}

.author-name {
  font-size: 2.5rem;
  font-weight: 800;
  background: #f1f5f9;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 1rem 0;
  letter-spacing: -0.05em;
  line-height: 1.2;
}

.author-bio {
  font-size: 1.125rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0 0 1.5rem 0;
  max-width: 600px;
}

.quick-stats {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
  background: rgba(59, 130, 246, 0.08);
  padding: 0.5rem 1rem;
  border-radius: 1rem;
  border: 1px solid rgba(59, 130, 246, 0.1);
  transition: all 0.3s ease;
}

.stat-item:hover {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.2);
  transform: scale(1.02);
}

/* 现代化统计卡片 */
.modern-stats-section {
  margin-bottom: 3rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.modern-stat-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 1.5rem;
  padding: 2rem;
  text-align: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
}

.modern-stat-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 
    0 20px 40px rgba(59, 130, 246, 0.06),
    0 2px 0 rgba(255, 255, 255, 0.6) inset;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
  color: white;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.stat-articles .stat-icon {
  background: #f1f5f9;
}

.stat-views .stat-icon {
  background: #f1f5f9;
}

.stat-likes .stat-icon {
  background: #f1f5f9;
}

.stat-date .stat-icon {
  background: #f1f5f9;
}

.modern-stat-card:hover .stat-icon {
  transform: scale(1.1) rotate(-5deg);
}

.stat-number {
  font-size: 2rem;
  font-weight: 800;
  background: #f1f5f9;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.5rem;
  letter-spacing: -0.025em;
}

.stat-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* 现代化文章列表 */
.modern-article-section {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 2rem;
  padding: 2.5rem;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.04),
    0 1px 0 rgba(255, 255, 255, 0.4) inset;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.5rem;
  font-weight: 700;
  background: #f1f5f9;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}

.title-icon {
  width: 32px;
  height: 32px;
  background: #f1f5f9;
  color: white;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.article-count-badge {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  padding: 0.5rem 1rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.articles-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.modern-article-card {
  background: rgba(248, 250, 252, 0.6);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 1.5rem;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.modern-article-card:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.08);
}

.article-link {
  display: block;
  padding: 2rem;
  text-decoration: none;
  color: inherit;
}

.article-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.article-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  line-height: 1.4;
  transition: color 0.3s ease;
}

.modern-article-card:hover .article-title {
  color: #3b82f6;
}

.article-arrow {
  color: #94a3b8;
  transition: all 0.3s ease;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: rgba(148, 163, 184, 0.1);
}

.modern-article-card:hover .article-arrow {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
  transform: translateX(4px);
}

.article-summary {
  color: #64748b;
  font-size: 0.875rem;
  line-height: 1.6;
  margin: 0 0 1.5rem 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-meta {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: #9ca3af;
  transition: color 0.3s ease;
}

.modern-article-card:hover .meta-item {
  color: #6b7280;
}

/* 空状态 */
.modern-empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-icon {
  color: #d1d5db;
  margin-bottom: 1rem;
}

.empty-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 0.5rem 0;
}

.empty-description {
  color: #6b7280;
  margin: 0;
}

/* 现代化分页 */
.modern-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
}

.pagination-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(8px);
}

.pagination-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}

.pagination-btn:disabled {
  background: rgba(156, 163, 175, 0.1);
  color: #9ca3af;
  border-color: rgba(156, 163, 175, 0.2);
  cursor: not-allowed;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.current-page {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  padding: 0.25rem 0.75rem;
  border-radius: 0.5rem;
  font-weight: 600;
}

/* 加载状态 */
.modern-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #f1f5f9;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(59, 130, 246, 0.1);
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  color: #6b7280;
  font-size: 0.875rem;
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .modern-author-profile {
    padding: 1rem;
  }
  
  .modern-author-header {
    padding: 2rem;
  }
  
  .header-content {
    flex-direction: column;
    text-align: center;
    gap: 1.5rem;
  }
  
  .author-name {
    font-size: 2rem;
  }
  
  .quick-stats {
    justify-content: center;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .modern-article-section {
    padding: 2rem;
  }
  
  .section-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
  
  .article-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .article-arrow {
    align-self: flex-end;
  }
  
  .modern-pagination {
    flex-direction: column;
    gap: 1rem;
  }
}

@media (max-width: 640px) {
  .avatar-container {
    width: 100px;
    height: 100px;
  }
  
  .author-name {
    font-size: 1.75rem;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .modern-stat-card {
    padding: 1.5rem;
  }
  
  .article-meta {
    gap: 1rem;
  }
}
</style>

<style scoped>
/* 作者公开页(公开站 V2):PageHead + 行列表 */
.author-page {
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
}
.page-head {
  max-width: 1440px;
  margin: 0 auto;
  padding: 48px 32px 28px;
}
.eyebrow {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 10px;
}
.page-head h1 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.04em;
}
.page-head p {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--muted);
}
.meta {
  display: flex;
  gap: 18px;
  color: var(--muted);
  font-size: 13px;
  margin-top: 14px;
}
.section {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 32px 44px;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.section-head h2 {
  font-size: 14px;
  margin: 0;
}
.meta {
  font-size: 12px;
  color: var(--muted);
}
.list {
  display: grid;
}
.row {
  display: grid;
  grid-template-columns: 84px 1fr auto;
  gap: 14px;
  align-items: center;
  min-height: 56px;
  border-top: 1px solid var(--line);
  padding: 6px 0;
}
.row:first-child {
  border-top: 0;
}
.row time {
  font-size: 12px;
  color: var(--muted);
}
.row-title {
  font-size: 14px;
  font-weight: 650;
  color: var(--text);
}
.row-title:hover {
  color: var(--primary, #2563eb);
}
.row-sub {
  display: block;
  font-size: 11px;
  color: var(--muted);
  margin-top: 4px;
}
.pager {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
.pager-info {
  font-size: 12px;
  color: var(--muted);
}
.ghost-btn {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface, #fff);
  color: var(--text-2, #3f3f46);
  font-size: 12px;
  cursor: pointer;
}
.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.loading {
  padding: 60px 20px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}
</style>
