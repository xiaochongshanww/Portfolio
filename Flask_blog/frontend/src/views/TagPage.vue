<template>
  <div class="tag-page" v-if="loaded">
    <h1>#{{ tagSlug }}</h1>
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
const route = useRoute();
const tagSlug = ref(route.params.slug);
const loaded = ref(false);
const articles = ref([]);
async function load(){
  loaded.value=false;
  try{
    const resp = await fetch(`/api/v1/articles/public?tag=${encodeURIComponent(tagSlug.value)}`);
    const j = await resp.json();
    articles.value = j.data?.list || [];
  }catch(e){ articles.value=[]; }
  const url = window.location.href;
  setMeta({ title: `标签: ${tagSlug.value}`, description: `标签 ${tagSlug.value} 下的文章`, image: articles.value[0]?.featured_image, url });
  injectJsonLd({ '@context':'https://schema.org', '@type':'CollectionPage', name:`标签: ${tagSlug.value}` , url, mainEntity:{ '@type':'ItemList', itemListElement: articles.value.map((a,i)=>({ '@type':'ListItem', position:i+1, url: window.location.origin + '/article/' + a.slug, name:a.title })) }});
  loaded.value=true;
}
function formatDate(dt){ if(!dt) return ''; return new Date(dt).toLocaleDateString(); }
onMounted(load);
watch(()=>route.params.slug, v=>{ if(v){ tagSlug.value=v; load(); }});
</script>
<style scoped>
.meta { margin-left:.5rem; color:#666; }
.empty { color:#888; padding:1rem; }
.loading { padding:2rem; text-align:center; }
</style>
