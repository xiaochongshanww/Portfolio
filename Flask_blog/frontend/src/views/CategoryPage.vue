<template>
  <div class="category-page" v-if="loaded">
    <h1>分类: {{ slugOrId }}</h1>
    <p class="desc" v-if="categoryName">{{ categoryName }}</p>
    <ul>
      <li v-for="a in articles" :key="a.id">
        <router-link :to="'/article/' + a.slug">{{ a.title }}</router-link>
        <small class="meta">{{ formatDate(a.published_at || a.created_at) }}</small>
      </li>
    </ul>
    <div v-if="!articles.length" class="empty">暂无文章</div>
  </div>
  <div v-else class="loading">加载中...</div>
</template>
<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { setMeta, injectJsonLd } from '../composables/useMeta';
import { API } from '../api';
const route = useRoute();
const loaded = ref(false);
const articles = ref([]);
const slugOrId = ref(route.params.slug || route.params.id);
const categoryName = ref('');
async function load(){
  loaded.value=false;
  // 获取分类列表匹配名称（简单方式：全部加载）
  try { const cats = (await API.TaxonomyService.listCategories()).data; const idNum = Number(slugOrId.value); const c = cats.find(c=>c.id===idNum); if(c) categoryName.value = c.name; } catch(e){}
  try{
    const resp = await fetch(`/api/v1/articles/public?category_id=${slugOrId.value}`);
    const j = await resp.json();
    articles.value = j.data?.list || [];
  }catch(e){ articles.value=[]; }
  const url = window.location.href;
  setMeta({ title: `分类: ${categoryName.value || slugOrId.value}`, description: `分类 ${categoryName.value || slugOrId.value} 下的文章`, image: articles.value[0]?.featured_image, url });
  injectJsonLd({
    '@context':'https://schema.org',
    '@type':'CollectionPage',
    name: `分类: ${categoryName.value || slugOrId.value}`,
    url,
    mainEntity: {
      '@type':'ItemList',
      itemListElement: articles.value.map((a,i)=>({ '@type':'ListItem', position:i+1, url: window.location.origin + '/article/' + a.slug, name:a.title }))
    }
  });
  loaded.value=true;
}
function formatDate(dt){ if(!dt) return ''; return new Date(dt).toLocaleDateString(); }
onMounted(load);
watch(()=>route.params.id, v=>{ if(v){ slugOrId.value=v; load(); }});
</script>
<style scoped>
.meta { margin-left:.5rem; color:#666; }
.empty { color:#888; padding:1rem; }
.loading { padding:2rem; text-align:center; }
</style>
