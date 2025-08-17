<template>
  <div class="author-profile" v-if="loaded">
    <header class="author-header">
  <img v-if="profile.avatar" :src="profile.avatar" class="avatar" loading="lazy" />
      <div class="meta">
  <h1>{{ profile.nickname || ('作者 #' + profile.id) }}</h1>
        <p class="bio" v-if="profile.bio">{{ profile.bio }}</p>
        <p class="stats" v-if="statsLoaded">
          <span>文章 {{ stats.articles_count }}</span>
          <span>总阅读 {{ stats.total_views }}</span>
          <span>总点赞 {{ stats.total_likes }}</span>
        </p>
      </div>
    </header>

    <section class="stats-cards" v-if="statsLoaded">
      <div class="card"><h3>文章数</h3><p>{{ stats.articles_count }}</p></div>
      <div class="card"><h3>总阅读</h3><p>{{ stats.total_views }}</p></div>
      <div class="card"><h3>总点赞</h3><p>{{ stats.total_likes }}</p></div>
      <div class="card" v-if="stats.last_published_at"><h3>最近发布</h3><p>{{ formatDate(stats.last_published_at) }}</p></div>
    </section>
    <section class="article-list">
      <h2>发布的文章</h2>
      <ul>
        <li v-for="a in articles" :key="a.id">
          <router-link :to="'/article/' + a.slug">
            <strong>{{ a.title }}</strong>
            <small class="meta-line">{{ a.views_count || 0 }} 次阅读 · {{ formatDate(a.published_at || a.created_at) }}</small>
          </router-link>
        </li>
      </ul>
      <div v-if="!articles.length" class="empty">暂无文章</div>
      <div class="pagination" v-if="total > pageSize">
        <button @click="prev" :disabled="page === 1">上一页</button>
        <button @click="next" :disabled="page * pageSize >= total">下一页</button>
      </div>
    </section>
  </div>
  <div v-else class="loading">加载中...</div>
</template>
<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useNotify } from '../composables/useNotify';
import { UsersService } from '../generated';
import { setMeta, injectJsonLd } from '../composables/useMeta';

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
.author-header { display:flex; gap:1rem; align-items:center; margin-bottom:1.5rem; }
.avatar { width:96px; height:96px; border-radius:50%; object-fit:cover; }
.meta-line { margin-left:.5rem; color:#666; }
.article-list ul { list-style:none; padding:0; }
.article-list li { margin:.5rem 0; }
.empty { color:#888; }
.loading { padding:2rem; text-align:center; }
.bio { color:#555; }
.stats span { margin-right:1rem; font-size:.85rem; color:#666; }
.pagination { margin-top:1rem; }
button { cursor:pointer; padding:.5rem 1rem; margin-right:.5rem; border:none; border-radius:.25rem; background-color:#007bff; color:white; }
button:disabled { background-color:#ccc; cursor:not-allowed; }
.stats-cards { display:flex; gap:1rem; flex-wrap:wrap; margin:1rem 0; }
.stats-cards .card { flex:1 1 140px; background:#f7f9fb; padding:0.75rem 1rem; border-radius:6px; box-shadow:0 0 0 1px #e3e6e9; }
.stats-cards .card h3 { margin:0 0 4px; font-size:.85rem; font-weight:600; color:#555; }
.stats-cards .card p { margin:0; font-size:1.1rem; font-weight:600; }
</style>
