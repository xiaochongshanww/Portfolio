<template>
  <div class="comments-section">
    <!-- 评论区标题 -->
    <div class="comments-header">
      <h3 class="comments-title">
        <el-icon class="title-icon"><ChatDotRound /></el-icon>
        评论区
        <span v-if="tree.length" class="comment-count">{{ tree.length }}</span>
      </h3>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span class="loading-text">加载评论中...</span>
    </div>
    
    <!-- 评论列表 -->
    <div v-else class="comments-content">
      <!-- 空状态 -->
      <div v-if="!tree.length" class="empty-state">
        <el-icon class="empty-icon"><ChatDotRound /></el-icon>
        <p class="empty-text">暂无评论，来发表第一条评论吧！</p>
      </div>
      
      <!-- 评论列表 -->
      <div v-else class="comment-list">
        <div v-for="comment in tree" :key="comment.id" class="comment-item">
          <div class="comment-content">
            <!-- 用户头像 -->
            <div class="user-avatar">
              <el-icon class="avatar-icon"><User /></el-icon>
            </div>
            
            <!-- 评论主体 -->
            <div class="comment-main">
              <div class="comment-header">
                <span class="user-name">{{ comment.user?.nickname || comment.user?.email || '匿名用户' }}</span>
                <span class="comment-time">{{ formatDate(comment.created_at) }}</span>
              </div>
              <div class="comment-text">{{ comment.content }}</div>
              
              <!-- 评论操作 -->
              <div class="comment-actions">
                <button class="action-btn" @click="prepareReply(comment)">
                  <el-icon><ChatLineSquare /></el-icon>
                  回复
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 评论编辑器 -->
    <div v-if="canComment" class="comment-editor">
      <div class="editor-header">
        <h4 class="editor-title">
          <span v-if="replyTo">回复 @{{ replyTo.user?.nickname || replyTo.id }}</span>
          <span v-else>发表评论</span>
        </h4>
        <el-button v-if="replyTo" @click="cancelReply" size="small" text>
          <el-icon><Close /></el-icon>
          取消回复
        </el-button>
      </div>
      
      <div class="editor-input-wrapper">
        <textarea 
          v-model="content" 
          placeholder="写下你的评论..."
          class="comment-textarea"
          :class="{ 'is-reply': replyTo }"
        />
        <div class="input-footer">
          <div class="input-info">
            <span class="char-count">{{ content.length }}/500</span>
          </div>
          <div class="input-actions">
            <el-button 
              @click="submit" 
              :disabled="submitting || !trimmed || content.length > 500" 
              type="primary"
              size="large"
              class="submit-btn"
              :loading="submitting"
            >
              <el-icon v-if="!submitting"><Position /></el-icon>
              {{ submitting ? '发布中...' : '发布评论' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 未登录提示 -->
    <div v-else-if="props.articleId" class="login-prompt">
      <el-icon class="prompt-icon"><Lock /></el-icon>
      <p class="prompt-text">
        请先
        <RouterLink to="/login" class="login-link">登录</RouterLink>
        后发表评论
      </p>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, defineAsyncComponent, watch } from 'vue';
import apiClient from '../apiClient';
import { useUserStore } from '../stores/user';
import { ElMessage, ElButton } from 'element-plus';
import { 
  ChatDotRound, 
  User, 
  ChatLineSquare, 
  Close, 
  Position, 
  Lock 
} from '@element-plus/icons-vue';
// const CommentNode = defineAsyncComponent(()=>import('./CommentNode.vue'));
const props = defineProps({ articleId: { type: Number, required: false, default: null }});
const userStore = useUserStore();
const loading = ref(false);
const submitting = ref(false);
/** @type {import('vue').Ref<Array<any>>} */
const tree = ref([]);
const content = ref('');
const replyTo = ref(null);
const canComment = computed(()=> !!userStore.token && !!props.articleId);
const trimmed = computed(()=> content.value.trim());

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleString('zh-CN');
  } catch {
    return '';
  }
}

async function load(){ 
  if(!props.articleId){ tree.value=[]; return; } 
  loading.value=true; 
  try { 
    const r = await apiClient.get(`/comments/article/${props.articleId}`); 
    tree.value = r.data?.data || []; 
  } catch(e){ 
    ElMessage.error('评论加载失败'); 
  } finally { 
    loading.value=false; 
  } 
}
function prepareReply(node){ replyTo.value = node; }
function cancelReply(){ replyTo.value=null; }
async function submit(){ 
  if(!trimmed.value || !props.articleId) return; 
  submitting.value=true; 
  try { 
    await apiClient.post('/comments/', { 
      article_id: props.articleId, 
      content: trimmed.value, 
      parent_id: replyTo.value?.id 
    }); 
    ElMessage.success('已提交，待审核'); 
    content.value=''; 
    replyTo.value=null; 
    await load(); 
  } catch(e){ 
    ElMessage.error('提交失败'); 
  } finally { 
    submitting.value=false; 
  } 
}
watch(()=>props.articleId, ()=>load());
onMounted(load);
</script>
<style scoped>
/* ====== 评论区主容器 ====== */
.comments-section {
  margin-top: 3rem;
  background: white;
  border-radius: 1rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  border: 1px solid rgb(229 231 235);
  overflow: hidden;
}

/* ====== 评论区标题 ====== */
.comments-header {
  padding: 1.5rem 2rem 1rem;
  background: linear-gradient(135deg, rgb(248 250 252) 0%, rgb(241 245 249) 100%);
  border-bottom: 1px solid rgb(229 231 235);
}

.comments-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.375rem;
  font-weight: 700;
  color: rgb(17 24 39);
  margin: 0;
}

.title-icon {
  color: rgb(59 130 246);
  font-size: 1.5rem;
}

.comment-count {
  background: rgb(59 130 246);
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: 0.5rem;
  min-width: 1.5rem;
  text-align: center;
}

/* ====== 加载状态 ====== */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem 2rem;
  color: rgb(107 114 128);
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgb(229 231 235);
  border-top: 2px solid rgb(59 130 246);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  font-size: 0.875rem;
}

/* ====== 空状态 ====== */
.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: rgb(107 114 128);
}

.empty-icon {
  font-size: 3rem;
  color: rgb(156 163 175);
  margin-bottom: 1rem;
}

.empty-text {
  font-size: 1rem;
  margin: 0;
}

/* ====== 评论内容区域 ====== */
.comments-content {
  padding: 0;
}

.comment-list {
  max-height: 500px;
  overflow-y: auto;
}

/* ====== 单个评论项 ====== */
.comment-item {
  border-bottom: 1px solid rgb(243 244 246);
  transition: background-color 0.2s ease;
}

.comment-item:hover {
  background: rgb(249 250 251);
}

.comment-item:last-child {
  border-bottom: none;
}

.comment-content {
  display: flex;
  gap: 1rem;
  padding: 1.5rem 2rem;
}

/* ====== 用户头像 ====== */
.user-avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: linear-gradient(135deg, rgb(59 130 246), rgb(139 92 246));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 6px rgb(0 0 0 / 0.1);
}

.avatar-icon {
  color: white;
  font-size: 1.25rem;
}

/* ====== 评论主体 ====== */
.comment-main {
  flex: 1;
  min-width: 0;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.user-name {
  font-weight: 600;
  color: rgb(17 24 39);
  font-size: 0.875rem;
}

.comment-time {
  font-size: 0.75rem;
  color: rgb(107 114 128);
}

.comment-text {
  color: rgb(55 65 81);
  font-size: 0.875rem;
  line-height: 1.6;
  margin-bottom: 0.75rem;
  word-wrap: break-word;
}

/* ====== 评论操作 ====== */
.comment-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: rgb(107 114 128);
  background: none;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgb(243 244 246);
  color: rgb(59 130 246);
}

/* ====== 评论编辑器 ====== */
.comment-editor {
  border-top: 1px solid rgb(229 231 235);
  background: rgb(249 250 251);
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem 0.5rem;
}

.editor-title {
  font-size: 1rem;
  font-weight: 600;
  color: rgb(17 24 39);
  margin: 0;
}

.editor-input-wrapper {
  padding: 0.5rem 2rem 2rem;
}

/* ====== 评论输入框 ====== */
.comment-textarea {
  width: 100%;
  min-height: 100px;
  padding: 1rem;
  border: 2px solid rgb(229 231 235);
  border-radius: 0.75rem;
  font-size: 0.875rem;
  line-height: 1.6;
  color: rgb(17 24 39);
  background: white;
  resize: vertical;
  transition: all 0.2s ease;
  font-family: inherit;
}

.comment-textarea:focus {
  outline: none;
  border-color: rgb(59 130 246);
  box-shadow: 0 0 0 3px rgb(59 130 246 / 0.1);
}

.comment-textarea.is-reply {
  border-left: 4px solid rgb(34 197 94);
  background: rgb(240 253 244);
}

.comment-textarea::placeholder {
  color: rgb(156 163 175);
}

/* ====== 输入框底部 ====== */
.input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1rem;
  gap: 1rem;
}

.input-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.char-count {
  font-size: 0.75rem;
  color: rgb(107 114 128);
}

.input-actions {
  display: flex;
  gap: 0.75rem;
}

/* ====== 提交按钮样式 ====== */
.submit-btn {
  background: linear-gradient(135deg, rgb(34 197 94), rgb(22 163 74)) !important;
  border: none !important;
  padding: 0.75rem 2rem !important;
  border-radius: 0.75rem !important;
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 6px rgb(34 197 94 / 0.25) !important;
  min-width: 120px;
}

.submit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgb(22 163 74), rgb(21 128 61)) !important;
  transform: translateY(-2px);
  box-shadow: 0 8px 12px rgb(34 197 94 / 0.35) !important;
}

.submit-btn:disabled {
  background: rgb(156 163 175) !important;
  transform: none !important;
  box-shadow: none !important;
  cursor: not-allowed;
}

/* ====== 未登录提示 ====== */
.login-prompt {
  text-align: center;
  padding: 2rem;
  background: rgb(249 250 251);
  border-top: 1px solid rgb(229 231 235);
}

.prompt-icon {
  font-size: 2rem;
  color: rgb(156 163 175);
  margin-bottom: 0.75rem;
}

.prompt-text {
  color: rgb(107 114 128);
  font-size: 0.875rem;
  margin: 0;
}

.login-link {
  color: rgb(59 130 246);
  font-weight: 600;
  text-decoration: none;
  transition: color 0.2s ease;
}

.login-link:hover {
  color: rgb(37 99 235);
  text-decoration: underline;
}

/* ====== 响应式设计 ====== */
@media (max-width: 768px) {
  .comments-header,
  .comment-content,
  .editor-input-wrapper {
    padding-left: 1rem;
    padding-right: 1rem;
  }
  
  .comment-content {
    gap: 0.75rem;
  }
  
  .user-avatar {
    width: 2rem;
    height: 2rem;
  }
  
  .avatar-icon {
    font-size: 1rem;
  }
  
  .input-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }
  
  .submit-btn {
    width: 100% !important;
  }
}

@media (max-width: 640px) {
  .comments-title {
    font-size: 1.125rem;
  }
  
  .comment-textarea {
    min-height: 80px;
    padding: 0.75rem;
  }
  
  .editor-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}

/* ====== Element Plus 样式覆盖 ====== */
:deep(.el-button) {
  border-radius: 0.5rem;
  font-weight: 500;
}

:deep(.el-button--text) {
  color: rgb(107 114 128);
  padding: 0.25rem 0.5rem;
}

:deep(.el-button--text):hover {
  background: rgb(243 244 246);
  color: rgb(59 130 246);
}
</style>
