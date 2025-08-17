<template>
  <div class="comments">
    <h3>评论</h3>
    <div v-if="loading">加载评论...</div>
    <div v-else>
      <div v-if="!tree.length">暂无评论</div>
      <ul class="comment-tree">
        <CommentNode v-for="n in tree" :key="n.id" :node="n" @reply="prepareReply" />
      </ul>
    </div>
    <div v-if="canComment" class="editor-box">
      <textarea v-model="content" placeholder="写下你的评论..." />
      <div class="actions">
        <button @click="submit" :disabled="submitting || !trimmed">发布</button>
        <button v-if="replyTo" @click="cancelReply" type="button">取消回复</button>
        <span v-if="replyTo" class="replying">回复 @{{ replyTo.id }}</span>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, defineAsyncComponent, watch } from 'vue';
import { API } from '../api';
import { useSessionStore } from '../stores/session';
import { useNotify } from '../composables/useNotify';
const CommentNode = defineAsyncComponent(()=>import('./CommentNode.vue'));
const props = defineProps({ articleId: { type: Number, required: false, default: null }});
const session = useSessionStore();
const { pushError, pushSuccess } = useNotify();
const loading = ref(false);
const submitting = ref(false);
/** @type {import('vue').Ref<Array<any>>} */
const tree = ref([]);
const content = ref('');
const replyTo = ref<any|null>(null);
const canComment = computed(()=> !!session.token && !!props.articleId);
const trimmed = computed(()=> content.value.trim());

async function load(){ if(!props.articleId){ tree.value=[]; return; } loading.value=true; try { const r = await API.CommentsService.getApiV1CommentsArticleTree(props.articleId); tree.value = r.data?.data || r.data || []; } catch(e){ pushError('评论加载失败'); } finally { loading.value=false; } }
function prepareReply(node){ replyTo.value = node; }
function cancelReply(){ replyTo.value=null; }
async function submit(){ if(!trimmed.value || !props.articleId) return; submitting.value=true; try { await API.CommentsService.postApiV1Comments({ article_id: props.articleId, content: trimmed.value, parent_id: replyTo.value?.id }); pushSuccess('已提交，待审核'); content.value=''; replyTo.value=null; await load(); } catch(e){ pushError('提交失败'); } finally { submitting.value=false; } }
watch(()=>props.articleId, ()=>load());
onMounted(load);
</script>
<style scoped>
.comments { margin-top:32px; }
.comment-tree { list-style:none; padding:0; display:flex; flex-direction:column; gap:12px; }
textarea { width:100%; min-height:80px; padding:8px; resize:vertical; }
.editor-box { margin-top:16px; }
.editor-box .actions { margin-top:8px; display:flex; gap:12px; align-items:center; }
.replying { font-size:12px; color:#888; }
</style>
