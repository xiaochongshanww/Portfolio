<template>
  <div v-if="loaded" class="tag-page shell">
    <section class="page-head">
      <div class="eyebrow">标签</div>
      <h1>#{{ tagSlug }}</h1>
      <p>{{ articles.length ? `共 ${articles.length} 篇文章` : '这个标签下还没有文章。' }}</p>
    </section>

    <section class="section section-last">
      <!-- empty -->
      <div v-if="!articles.length" class="state-block">暂无文章,去看看其他标签或专题。</div>

      <!-- rows -->
      <div v-else class="article-list">
        <ArticleFeedRow
          v-for="a in articles"
          :key="a.id"
          :title="a.title"
          :summary="a.summary || ''"
          :published-at="a.published_at || a.created_at || ''"
          :href="'/article/' + a.slug"
        />
      </div>
    </section>
  </div>
  <div v-else class="tag-page shell tag-loading">
    <el-skeleton :rows="6" animated />
  </div>
</template>
<script setup lang="ts">
/**
 * 标签页(A5 决策:保留原页,轻量对齐公开站 V2)
 * shell + PageHead + ArticleFeedRow;数据流保持原状:getPublicArticles({ tag })。
 */
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { API } from '../api';
import type { Article } from '@/types';
import ArticleFeedRow from '../components/public/ArticleFeedRow.vue';
import { setMeta, injectJsonLd } from '../composables/useMeta';
const props = withDefaults(defineProps<{ slug?: string }>(), { slug: "" })
const route = useRoute();
const tagSlug = ref(props.slug || route.params.slug);
const loaded = ref(false);
/** @type {import('vue').Ref<Article[]>} */
const articles = ref<Article[]>([]);
async function load(){
  loaded.value=false;
  try{
    const resp = await API.getPublicArticles({ tag: String(tagSlug.value) });
    const j = resp.data;
    articles.value = j.data?.list || [];
  }catch(e){ articles.value=[]; }
  const url = window.location.href;
  setMeta({ title: `标签: ${tagSlug.value}`, description: `标签 ${tagSlug.value} 下的文章`, image: articles.value[0]?.featured_image, url });
  injectJsonLd({ '@context':'https://schema.org', '@type':'CollectionPage', name:`标签: ${tagSlug.value}` , url, mainEntity:{ '@type':'ItemList', itemListElement: articles.value.map((a,i)=>({ '@type':'ListItem', position:i+1, url: window.location.origin + '/article/' + a.slug, name:a.title })) }});
  loaded.value=true;
}
onMounted(load);
watch(() => props.slug || route.params.slug, v=>{ if(v){ tagSlug.value=v; load(); }});
</script>
<style scoped>
.page-head {
  padding: 38px 0 24px;
  border-bottom: 1px solid var(--line);
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
  color: var(--text);
}
.page-head p {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--muted);
}
.section {
  padding: 22px 0 34px;
}
.section-last {
  border-bottom: 0;
}
.article-list {
  display: grid;
  gap: 2px;
}
.state-block {
  border: 1px dashed var(--line-strong);
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}
.tag-loading {
  padding-top: 48px;
  padding-bottom: 48px;
}
</style>
