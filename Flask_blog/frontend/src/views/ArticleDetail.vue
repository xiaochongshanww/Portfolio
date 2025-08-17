<template>
  <div class="max-w-4xl mx-auto py-4">
    <div v-if="loading" class="p-8">
        <el-skeleton :rows="10" animated />
    </div>
    <div v-else-if="error" class="p-8">
        <el-alert :title="error" type="error" show-icon :closable="false" />
    </div>
    <article v-else-if="article" class="bg-white shadow-sm rounded-lg">
        <!-- Header -->
        <div class="p-6 md:p-8">
            <p class="text-sm text-gray-500">状态: <el-tag size="small">{{ article.status }}</el-tag></p>
            <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight text-gray-900 my-4">{{ article.title }}</h1>
            <div class="flex items-center gap-4 text-sm text-gray-500">
                <span>发布于 {{ new Date(article.published_at || article.created_at).toLocaleDateString() }}</span>
                <span v-if="article.tags && article.tags.length" class="flex items-center gap-2">
                    <el-tag v-for="t in article.tags" :key="t" size="small" type="info">#{{ t }}</el-tag>
                </span>
            </div>
        </div>

        <!-- Featured Image -->
        <div v-if="article.featured_image" class="my-2">
            <img :src="article.featured_image" :alt="article.title" class="w-full h-auto object-cover" />
        </div>

        <!-- Workflow Actions (for editors/admins) -->
        <div v-if="nextList.length || canSchedule || canUnschedule || canUnpublish" class="p-4 m-6 bg-yellow-50 border border-yellow-200 rounded-md flex flex-wrap items-center gap-3">
            <span class="font-semibold">快速操作:</span>
            <el-button v-for="n in nextList" :key="n" @click="doTransition(n)" :disabled="acting || !canOperate(n)" size="small">{{ n }}</el-button>
            <el-button v-if="canSchedule" @click="schedule" :disabled="acting" size="small">定时发布</el-button>
            <el-button v-if="canUnschedule" @click="unschedule" :disabled="acting" size="small">取消定时</el-button>
            <el-button v-if="canUnpublish" @click="unpublish" :disabled="acting" size="small" type="warning">下线</el-button>
        </div>

        <!-- Article Body -->
        <div class="p-6 md:p-8 article-body" v-html="article.content_html"></div>

        <!-- Like/Bookmark Actions -->
        <div class="p-6 md:p-8 flex items-center gap-4 border-t">
            <el-button @click="toggleLike" :disabled="liking" :type="liked ? 'primary' : 'default'" round>
                {{ liked ? '已赞' : '点赞' }} ({{ likeCount }})
            </el-button>
            <el-button @click="toggleBookmark" :disabled="bookmarking" :type="bookmarked ? 'warning' : 'default'" round>
                {{ bookmarked ? '已收藏' : '收藏' }}
            </el-button>
        </div>

        <!-- Comments -->
        <div class="p-6 md:p-8 border-t">
            <h2 class="text-2xl font-bold mb-4">评论</h2>
            <CommentsThread :article-id="article.id" />
        </div>

        <!-- Versions Panel (for editors/admins) -->
        <section v-if="session.role === 'editor' || session.role === 'admin'" class="p-6 md:p-8 border-t bg-gray-50">
            <div class="flex justify-between items-center">
                <h3 class="text-lg font-semibold">版本历史</h3>
                <div>
                    <el-button @click="snapshot" :disabled="!article || loading" size="small">创建快照</el-button>
                    <el-button @click="()=>{showVersions=!showVersions; if(showVersions) loadVersions();}" size="small">{{ showVersions? '隐藏版本' : '显示版本' }}</el-button>
                </div>
            </div>
            <div v-if="showVersions" class="mt-4">
                <div v-if="versionsLoading"><el-skeleton :rows="3" animated /></div>
                <ul v-else class="space-y-2">
                    <li v-for="v in versions" :key="v.version_no" class="text-sm bg-white p-2 border rounded-md flex items-center justify-between">
                        <span>v{{ v.version_no }} @ {{ new Date(v.created_at).toLocaleString() }}</span>
                        <div class="space-x-2">
                            <el-button text type="primary" size="small" @click="rollback(v)">回滚</el-button>
                            <el-button text type="primary" size="small" v-if="selectedVersion && selectedVersion.version_no!==v.version_no" @click="showDiffWith(v.version_no)">与当前比对</el-button>
                            <el-button text size="small" v-else @click="selectBase(v)">选中</el-button>
                        </div>
                    </li>
                    <li v-if="!versions.length" class="text-sm text-gray-500">暂无版本</li>
                </ul>
                <div v-if="diff.loading" class="mt-4 p-4 border rounded-md bg-white">差异加载中...</div>
                <div v-else-if="diff.lines.length" class="mt-4 border rounded-md overflow-hidden">
                    <h4 class="text-sm font-semibold p-2 bg-gray-100 border-b">Diff v{{ diff.from }} → v{{ diff.to }}</h4>
                    <pre class="text-xs leading-relaxed p-2 overflow-x-auto"><code>
                        <span v-for="(line,i) in diff.lines" :key="i" :class="diffLineClass(line)">{{ line }}</span>
                    </code></pre>
                </div>
                <div v-else-if="selectedVersion" class="mt-2 text-xs text-gray-500">已选择 v{{ selectedVersion.version_no }}，请选择另一个版本以查看差异。</div>
            </div>
        </section>
    </article>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useSessionStore } from '../stores/session';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';
import { ElMessage, ElMessageBox } from 'element-plus';
import CommentsThread from '../components/CommentsThread.vue';
import apiClient from '../apiClient'; // Simplified

// Mocked services for demonstration
const API = {
    ArticlesService: {
        getArticleBySlug: (slug) => apiClient.get(`/articles/slug/${slug}`),
        likeArticle: (id) => apiClient.post(`/articles/${id}/like`),
        bookmarkArticle: (id) => apiClient.post(`/articles/${id}/bookmark`),
        getVersions: (id) => apiClient.get(`/articles/${id}/versions`),
        createVersion: (id) => apiClient.post(`/articles/${id}/versions`),
        rollbackVersion: (id, vNo) => apiClient.post(`/articles/${id}/versions/${vNo}/rollback`),
        diffVersions: (id, vNo, targetNo) => apiClient.get(`/articles/${id}/versions/${vNo}/diff?target=${targetNo}`),
        submitArticle: (id) => apiClient.post(`/articles/${id}/submit`),
        approveArticle: (id) => apiClient.post(`/articles/${id}/approve`),
        rejectArticle: (id, reason) => apiClient.post(`/articles/${id}/reject`, { reason }),
        scheduleArticle: (id, date) => apiClient.post(`/articles/${id}/schedule`, { scheduled_at: date }),
        unpublishArticle: (id) => apiClient.post(`/articles/${id}/unpublish`),
        unscheduleArticle: (id) => apiClient.post(`/articles/${id}/unschedule`),
    }
}

const route = useRoute();
const session = useSessionStore();
const article = ref(null);
const liked = ref(false);
const bookmarked = ref(false);
const likeCount = ref(0);
const liking = ref(false);
const bookmarking = ref(false);
const loading = ref(false);
const acting = ref(false);
const error = ref('');
const versions = ref([]);
const versionsLoading = ref(false);
const showVersions = ref(false);
const selectedVersion = ref(null);
const diff = ref({ from:null, to:null, lines:[], loading:false });

const WORKFLOW_TRANSITIONS = {
    draft: ['submit'],
    pending: ['approve', 'reject'],
}

const nextList = computed(()=> article.value ? (WORKFLOW_TRANSITIONS[article.value.status] || []) : []);
const canOperate = (target) => true; // Simplified for demo
const canSchedule = computed(()=> article.value && article.value.status === 'draft');
const canUnschedule = computed(()=> article.value && article.value.status === 'scheduled');
const canUnpublish = computed(()=> article.value && article.value.status === 'published');

async function doTransition(target){
  if(!article.value) return;
  acting.value=true; error.value='';
  try {
    const id = article.value.id;
    if(target==='submit') await API.ArticlesService.submitArticle(id);
    else if(target==='approve') await API.ArticlesService.approveArticle(id);
    else if(target==='reject') await API.ArticlesService.rejectArticle(id, 'Rejected from UI');
    ElMessage.success('操作成功');
    await load();
  } catch(e){ ElMessage.error('操作失败'); } 
  finally { acting.value=false; }
}

async function load(){
  loading.value = true; error.value='';
  try {
    const slug = route.params.slug;
    const resp = await API.ArticlesService.getArticleBySlug(slug);
    const data = resp.data.data;
    article.value = data;
    likeCount.value = data.likes_count || 0;
    liked.value = !!data.liked;
    bookmarked.value = !!data.bookmarked;
    await highlightLater();
  } catch(e){ error.value = e.response?.data?.message || '加载文章失败'; } 
  finally { loading.value=false; }
}
onMounted(load);

async function schedule(){
  if(!article.value) return; 
  const date = new Date(Date.now()+3600_000).toISOString();
  await API.ArticlesService.scheduleArticle(article.value.id, date).then(load);
}
async function unpublish(){ await API.ArticlesService.unpublishArticle(article.value.id).then(load); }
async function unschedule(){ await API.ArticlesService.unscheduleArticle(article.value.id).then(load); }

async function loadVersions(){
  versionsLoading.value=true;
  const r = await API.ArticlesService.getVersions(article.value.id);
  versions.value = r.data.data;
  versionsLoading.value=false;
}

function selectBase(v){ selectedVersion.value = v; diff.value={ from:null,to:null,lines:[],loading:false }; }

async function showDiffWith(otherVersionNo){
  diff.value={ from:selectedVersion.value.version_no, to:otherVersionNo, lines:[], loading:true };
  const r = await API.ArticlesService.diffVersions(article.value.id, selectedVersion.value.version_no, otherVersionNo);
  diff.value = { ...r.data.data, loading:false };
}

function diffLineClass(line){
  if(line.startsWith('+')) return 'bg-green-50 text-green-700';
  if(line.startsWith('-')) return 'bg-red-50 text-red-700';
  if(line.startsWith('@@')) return 'bg-yellow-50 text-yellow-700 font-bold';
  return '';
}

async function snapshot(){ await API.ArticlesService.createVersion(article.value.id).then(loadVersions); }
async function rollback(v){ 
    await ElMessageBox.confirm(`确定要回滚到版本 ${v.version_no} 吗?`, '警告', { type: 'warning' });
    await API.ArticlesService.rollbackVersion(article.value.id, v.version_no).then(load);
}

async function toggleLike(){
  liking.value=true;
  await API.ArticlesService.likeArticle(article.value.id);
  const r = await API.ArticlesService.getArticleBySlug(route.params.slug);
  likeCount.value = r.data.data.likes_count;
  liked.value = r.data.data.liked;
  liking.value=false;
}
async function toggleBookmark(){
  bookmarking.value=true;
  await API.ArticlesService.bookmarkArticle(article.value.id);
  bookmarked.value = !bookmarked.value;
  bookmarking.value=false;
}

async function highlightLater(){
  await nextTick();
  document.querySelectorAll('.article-body pre code').forEach(block=>{ try { hljs.highlightElement(block); } catch{} });
}

watch(()=>article.value, (newVal) => {
    if (newVal) {
        highlightLater();
    }
}, { deep: true });

</script>