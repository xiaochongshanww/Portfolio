<template>
  <div class="search-page">
    <form @submit.prevent="doSearch" class="search-bar">
      <el-input v-model="q" placeholder="搜索文章..." class="flex1" clearable @keyup.enter="doSearch">
        <template #append>
          <el-button type="primary" :loading="loading" @click="doSearch">搜索</el-button>
        </template>
      </el-input>
      <el-select v-model="sort" class="w160">
        <el-option label="相关度" value="relevance" />
        <el-option label="最新" value="-published_at" />
        <el-option label="最多阅读" value="-views_count" />
        <el-option label="最多点赞" value="-likes_count" />
      </el-select>
      <el-input v-model="tagsRaw" placeholder="标签(逗号)" class="w160" clearable />
      <el-select v-model="matchMode" class="w120">
        <el-option label="标签并且" value="and" />
        <el-option label="标签或" value="or" />
      </el-select>
      <el-date-picker v-model="dateFrom" type="date" placeholder="起始日期" class="w160" />
      <el-date-picker v-model="dateTo" type="date" placeholder="结束日期" class="w160" />
    </form>
    <aside class="facets" v-if="Object.keys(facets).length">
      <div class="facet" v-if="facets.tags">
        <h4>标签</h4>
        <ul>
          <li v-for="(count, slug) in limitedFacet(facets.tags)" :key="slug">
            <label><input type="checkbox" :value="slug" v-model="selectedFacetTags" @change="applyFacetTags"/> {{ slug }} ({{ count }})</label>
          </li>
        </ul>
      </div>
      <div class="facet" v-if="facets.category_id">
        <h4>分类</h4>
        <ul>
          <li v-for="(count, cid) in facets.category_id" :key="cid">
            <button type="button" :class="{active: categoryId===cid}" @click="toggleCategory(cid)">#{{ cid }} ({{ count }})</button>
          </li>
        </ul>
      </div>
      <div class="facet" v-if="facets.author_id">
        <h4>作者</h4>
        <ul>
          <li v-for="(count, aid) in facets.author_id" :key="aid">
            <button type="button" :class="{active: authorId===aid}" @click="toggleAuthor(aid)">@{{ aid }} ({{ count }})</button>
          </li>
        </ul>
      </div>
    </aside>

    <div class="results" v-if="results.length">
      <p class="hint">共 {{ total }} 条结果</p>
      <ul>
        <li v-for="r in results" :key="r.id">
          <router-link :to="'/article/' + r.slug">
            <strong v-html="r.title"></strong>
            <small class="meta">{{ r.views_count || 0 }} 阅读 · {{ formatDate(r.published_at || r.created_at) }}</small>
            <p class="excerpt" v-html="r.excerpt"></p>
            <span class="tag" v-for="t in r.tags || []" :key="t">#{{ t }}</span>
          </router-link>
        </li>
      </ul>
      <div class="pager" v-if="total > pageSize">
        <el-button @click="page-- && doSearch()" :disabled="page===1">上一页</el-button>
        <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <el-button @click="page++ && doSearch()" :disabled="page>= total/pageSize">下一页</el-button>
      </div>
    </div>
    <div v-else-if="searched && !loading" class="empty">无结果</div>
    <div v-if="loading" class="loading">搜索中...</div>
  </div>
</template>
<script setup>
import { ref } from 'vue';
import { setMeta, injectJsonLd } from '../composables/useMeta';
import { API } from '../api';
import { useNotify } from '../composables/useNotify';

const { pushError } = useNotify();
const q = ref('');
const sort = ref('relevance');
const tagsRaw = ref('');
const matchMode = ref('and');
const results = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const loading = ref(false);
const searched = ref(false);
const dateFrom = ref('');
const dateTo = ref('');
const facets = ref({});
const categoryMap = ref({});
const authorMap = ref({});
const selectedFacetTags = ref([]);
const categoryId = ref();
const authorId = ref();

function limitedFacet(obj) {
  // 排序后截取前 20
  return Object.fromEntries(Object.entries(obj).sort((a,b)=>b[1]-a[1]).slice(0,20));
}
function applyFacetTags(){
  tagsRaw.value = selectedFacetTags.value.join(',');
  page.value = 1; doSearch();
}
function toggleCategory(cid){
  categoryId.value = categoryId.value===cid? undefined : cid; page.value=1; doSearch();
}
function toggleAuthor(aid){
  authorId.value = authorId.value===aid? undefined : aid; page.value=1; doSearch();
}

async function loadMaps(){
  try { const cats = (await API.TaxonomyService.listCategories()).data; categoryMap.value = Object.fromEntries(cats.map(c=>[String(c.id), c.name])); } catch(e){}
  try { const users = (await API.UsersService.getApiV1Users(1,100)).data?.list || []; authorMap.value = Object.fromEntries(users.map(u=>[String(u.id), u.nickname || ('用户'+u.id)])); } catch(e){}
}
loadMaps();

async function doSearch() {
  if (!q.value.trim()) return;
  loading.value = true;
  try {
  const resp = await API.SearchService.search({ q: q.value, page: page.value, page_size: pageSize, tags: tagsRaw.value || undefined, match: matchMode.value, category_id: categoryId.value? Number(categoryId.value): undefined, author_id: authorId.value? Number(authorId.value): undefined, sort: sort.value, date_from: dateFrom.value || undefined, date_to: dateTo.value || undefined, facets: 'tags,category_id,author_id' });
  const data = resp.data || resp; // 生成器可能已包装
  const list = data?.data?.list || data.list || [];
  results.value = list;
  results.value = results.value.map(r=>({ ...r, excerpt: r.highlight?.content || r.excerpt || '' }));
    total.value = data?.data?.total || resp.total || results.value.length; // 兜底
    facets.value = data?.data?.facets || {};
    searched.value = true;
    const totalPages = Math.max(1, Math.ceil(total.value / pageSize));
    const prevUrl = page.value>1 ? buildPageUrl(page.value-1) : undefined;
    const nextUrl = page.value< totalPages ? buildPageUrl(page.value+1) : undefined;
    setMeta({ title: `搜索: ${q.value}`, description: `关于 ${q.value} 的搜索结果，共 ${total.value} 条`, prevUrl, nextUrl, url: buildPageUrl(page.value) });
    injectJsonLd({ '@context':'https://schema.org', '@type':'SearchResultsPage', name:`搜索: ${q.value}`, query:q.value, totalResults: total.value, itemListElement: results.value.map((r,i)=>({ '@type':'ListItem', position:i+1, url: window.location.origin + '/article/' + r.slug, name:r.title })) });
  } catch(e) {
    pushError('搜索失败');
  } finally {
    loading.value = false;
  }
}

function formatDate(dt) { if(!dt) return ''; return new Date(dt).toLocaleDateString(); }
function buildPageUrl(p){ const u=new URL(window.location.href); u.searchParams.set('q', q.value); u.searchParams.set('page', p); return u.toString(); }
function clearFilters(){ selectedFacetTags.value=[]; tagsRaw.value=''; categoryId.value=undefined; authorId.value=undefined; dateFrom.value=''; dateTo.value=''; page.value=1; doSearch(); }
</script>
<style scoped>
.search-bar { display:flex; gap:.5rem; margin-bottom:1rem; flex-wrap:wrap; }
.flex1 { flex:1; min-width: 240px; }
.w160 { width: 160px; }
.w140 { width: 140px; }
.w120 { width: 120px; }
.facets { margin:1rem 0; display:flex; gap:2rem; flex-wrap:wrap; }
.facets h4 { margin:.25rem 0; font-size:.9rem; }
.facets ul { list-style:none; padding:0; margin:0; max-width:200px; }
.facets li { font-size:.75rem; margin:.25rem 0; }
.facet button { background:#f5f5f5; border:1px solid #ddd; padding:2px 6px; cursor:pointer; border-radius:3px; }
.facet button.active { background:#409eff; color:#fff; border-color:#409eff; }
.results ul { list-style:none; padding:0; }
.results li { margin:.75rem 0; }
.meta { margin-left:.5rem; color:#666; }
.excerpt { color:#444; font-size:.85rem; margin:.25rem 0; }
.excerpt mark { background:#ffe58f; }
.tag { display:inline-block; font-size:12px; margin-right:6px; color:#555; }
.pager { display:flex; align-items:center; gap:.75rem; margin-top:1rem; }
.empty, .loading { padding:2rem; text-align:center; color:#666; }
</style>
