<template>
  <div class="modern-author-profile" v-if="loaded">
    <!-- 现代化作者头部 -->
    <header class="modern-author-header">
      <div class="header-decoration"></div>
      <div class="header-content">
        <div class="avatar-section">
          <div class="avatar-container">
            <img v-if="profile.avatar" :src="profile.avatar" class="modern-avatar" loading="lazy" />
            <div v-else class="avatar-placeholder">
              <el-icon size="48"><User /></el-icon>
            </div>
            <div class="avatar-ring"></div>
          </div>
        </div>
        <div class="author-meta">
          <h1 class="author-name">{{ profile.nickname || ('作者 #' + profile.id) }}</h1>
          <p class="author-bio" v-if="profile.bio">{{ profile.bio }}</p>
          <div class="quick-stats" v-if="statsLoaded">
            <span class="stat-item">
              <el-icon><Document /></el-icon>
              {{ stats.articles_count }} 篇文章
            </span>
            <span class="stat-item">
              <el-icon><View /></el-icon>
              {{ stats.total_views }} 次阅读
            </span>
            <span class="stat-item">
              <el-icon><Star /></el-icon>
              {{ stats.total_likes }} 点赞
            </span>
          </div>
        </div>
      </div>
    </header>

    <!-- 现代化统计卡片 -->
    <section class="modern-stats-section" v-if="statsLoaded">
      <div class="stats-grid">
        <div class="modern-stat-card stat-articles">
          <div class="stat-icon">
            <el-icon size="24"><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ stats.articles_count }}</div>
            <div class="stat-label">文章数</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        <div class="modern-stat-card stat-views">
          <div class="stat-icon">
            <el-icon size="24"><View /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ stats.total_views }}</div>
            <div class="stat-label">总阅读</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        <div class="modern-stat-card stat-likes">
          <div class="stat-icon">
            <el-icon size="24"><Star /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ stats.total_likes }}</div>
            <div class="stat-label">总点赞</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
        <div class="modern-stat-card stat-date" v-if="stats.last_published_at">
          <div class="stat-icon">
            <el-icon size="24"><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-number">{{ formatDate(stats.last_published_at) }}</div>
            <div class="stat-label">最近发布</div>
          </div>
          <div class="stat-decoration"></div>
        </div>
      </div>
    </section>
    <!-- 现代化文章列表 -->
    <section class="modern-article-section">
      <div class="section-header">
        <h2 class="section-title">
          <el-icon class="title-icon"><Collection /></el-icon>
          发布的文章
        </h2>
        <div class="article-count-badge">{{ total }} 篇</div>
      </div>
      
      <div class="articles-container">
        <article 
          v-for="article in articles" 
          :key="article.id"
          class="modern-article-card group"
        >
          <router-link :to="'/article/' + article.slug" class="article-link">
            <div class="article-content">
              <div class="article-header">
                <h3 class="article-title">{{ article.title }}</h3>
                <div class="article-arrow">
                  <el-icon><ArrowRight /></el-icon>
                </div>
              </div>
              
              <p class="article-summary" v-if="article.summary">
                {{ article.summary }}
              </p>
              
              <div class="article-meta">
                <span class="meta-item">
                  <el-icon size="14"><View /></el-icon>
                  {{ article.views_count || 0 }} 次阅读
                </span>
                <span class="meta-item">
                  <el-icon size="14"><Calendar /></el-icon>
                  {{ formatDate(article.published_at || article.created_at) }}
                </span>
                <span class="meta-item" v-if="article.category">
                  <el-icon size="14"><Folder /></el-icon>
                  {{ article.category.name }}
                </span>
              </div>
            </div>
            
            <div class="article-decoration"></div>
          </router-link>
        </article>
      </div>
      
      <!-- 空状态 -->
      <div v-if="!articles.length" class="modern-empty-state">
        <el-icon class="empty-icon" size="64"><Document /></el-icon>
        <h3 class="empty-title">暂无文章</h3>
        <p class="empty-description">该作者还没有发布任何文章</p>
      </div>
      
      <!-- 现代化分页 -->
      <div class="modern-pagination" v-if="total > pageSize">
        <button 
          @click="prev" 
          :disabled="page === 1"
          class="pagination-btn prev-btn"
        >
          <el-icon><ArrowLeft /></el-icon>
          上一页
        </button>
        
        <div class="page-info">
          <span class="current-page">{{ page }}</span>
          <span class="page-separator">/</span>
          <span class="total-pages">{{ Math.ceil(total / pageSize) }}</span>
        </div>
        
        <button 
          @click="next" 
          :disabled="page * pageSize >= total"
          class="pagination-btn next-btn"
        >
          下一页
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>
    </section>
  </div>
  <!-- 现代化加载状态 -->
  <div v-else class="modern-loading">
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载中...</p>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useNotify } from '../composables/useNotify';
import { UsersService } from '../generated';
import { setMeta, injectJsonLd } from '../composables/useMeta';
import { 
  User, Document, View, Star, Clock, Collection, ArrowRight, Calendar, 
  Folder, ArrowLeft 
} from '@element-plus/icons-vue';

const route = useRoute();
const { pushError } = useNotify();

const userId = ref(Number(route.params.id));
const profile = ref({});
const articles = ref([]);
const stats = ref({ articles_count:0,total_views:0,total_likes:0,last_published_at:null });
const statsLoaded = ref(false);
const loaded = ref(false);
const page = ref(1);
const pageSize = 10;
const total = ref(0);

async function loadProfile(){
  try {
    const r = await UsersService.getApiV1UsersPublic(userId.value);
    profile.value = r.data?.data || r.data || r; // 兼容包装
  } catch(e){ pushError('作者信息获取失败'); }
}
async function loadStats(){
  try {
    const r = await fetch(`/api/v1/users/public/${userId.value}/stats`);
    const j = await r.json();
    if(j && j.data) stats.value = j.data; statsLoaded.value=true;
  }catch(e){ statsLoaded.value=true; }
}
async function loadArticles(){
  try {
    const r = await UsersService.getApiV1UsersPublicArticles(userId.value, page.value, pageSize, '-published_at');
    const data = r.data?.data || r.data || r;
    // data 可能是 ArticleListResponse
    articles.value = data.list || data.items || [];
    total.value = data.total || articles.value.length;
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
function formatDate(dt){ if(!dt) return ''; return new Date(dt).toLocaleDateString(); }
function prev(){ if(page.value>1){ page.value--; loadArticles(); } }
function next(){ if(page.value*pageSize < total.value){ page.value++; loadArticles(); } }
function buildPageUrl(p){ const u=new URL(window.location.href); u.searchParams.set('page', p); return u.toString(); }

onMounted(load);
watch(()=>route.params.id, v=>{ userId.value=Number(v); page.value=1; load(); });
</script>
<style scoped>
/* ===== 现代化作者主页样式 ===== */
.modern-author-profile {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem 1rem;
  background: 
    radial-gradient(circle at 20% 50%, rgba(59, 130, 246, 0.04) 0%, transparent 40%),
    radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.04) 0%, transparent 40%),
    radial-gradient(circle at 40% 80%, rgba(16, 185, 129, 0.04) 0%, transparent 40%),
    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 30%, #ffffff 70%, #fafbfe 100%);
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
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #10b981, #f59e0b);
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
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
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
  background: linear-gradient(45deg, #3b82f6, #8b5cf6, #06b6d4) border-box;
  mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
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
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 50%, #8b5cf6 100%);
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
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
}

.stat-views .stat-icon {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.stat-likes .stat-icon {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.stat-date .stat-icon {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
}

.modern-stat-card:hover .stat-icon {
  transform: scale(1.1) rotate(-5deg);
}

.stat-number {
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
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
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}

.title-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
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
  background: 
    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 30%, #ffffff 70%, #fafbfe 100%);
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
