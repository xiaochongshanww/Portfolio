<template>
  <div class="comments-moderation-page">
    <h1>评论审核</h1>
    <p>这里列出了所有等待审核的评论。</p>

    <el-table :data="comments" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="80"></el-table-column>
      <el-table-column prop="content" label="评论内容" min-width="250">
        <template #default="scope">
          <div class="comment-content">{{ scope.row.content }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="user_id" label="用户ID" width="100"></el-table-column>
      <el-table-column prop="article_id" label="文章ID" width="100"></el-table-column>
      <el-table-column prop="created_at" label="提交时间" width="180">
        <template #default="scope">
          {{ new Date(scope.row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="scope">
          <el-button size="small" type="success" @click="handleModerate(scope.row.id, 'approve')">批准</el-button>
          <el-button size="small" type="warning" @click="handleModerate(scope.row.id, 'reject')">拒绝</el-button>
          <!-- 物理删除功能后端暂未提供，此处注释 -->
          <!-- <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button> -->
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-toolbar">
        <el-pagination
            background
            layout="prev, pager, next, total"
            :total="pagination.total"
            :current-page="pagination.page"
            :page-size="pagination.pageSize"
            @current-change="handlePageChange"
        />
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import apiClient from '../apiClient';

const comments = ref([]);
const loading = ref(false);
const pagination = reactive({
  total: 0,
  page: 1,
  pageSize: 10,
});

// --- API 调用封装 ---
const api = {
  getPendingComments: (page, pageSize) => 
    apiClient.get(`/comments/pending?page=${page}&page_size=${pageSize}`),
  moderateComment: (id, action) => 
    apiClient.post(`/comments/moderate/${id}`, { action }),
};

// --- 数据获取 ---
const fetchPendingComments = async () => {
  loading.value = true;
  try {
    const response = await api.getPendingComments(pagination.page, pagination.pageSize);
    const responseData = response.data.data;
    comments.value = responseData.list;
    pagination.total = responseData.total;
  } catch (error) {
    ElMessage.error('获取待审核评论列表失败');
    console.error(error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchPendingComments();
});

// --- 分页操作 ---
const handlePageChange = (newPage) => {
  pagination.page = newPage;
  fetchPendingComments();
};

// --- 审核操作 ---
const handleModerate = async (id, action) => {
  try {
    await api.moderateComment(id, action);
    ElMessage.success(`操作成功：${action === 'approve' ? '已批准' : '已拒绝'}`);
    
    // 从列表中移除已处理的评论
    const index = comments.value.findIndex(c => c.id === id);
    if (index !== -1) {
      comments.value.splice(index, 1);
    }

    // 如果当前页为空，尝试重新加载数据（可能会请求前一页）
    if (comments.value.length === 0 && pagination.total > 0) {
        // 简单处理：回到第一页或留在当前页刷新
        if (pagination.page > 1 && pagination.total -1 <= (pagination.page - 1) * pagination.pageSize) {
            pagination.page = pagination.page - 1;
        }
        fetchPendingComments();
    }

  } catch (error) {
    const errMsg = error.response?.data?.message || '操作失败';
    ElMessage.error(errMsg);
    console.error(error);
  }
};

</script>

<style scoped>
.comments-moderation-page {
  padding: 20px;
}
.comment-content {
  white-space: pre-wrap; /* 保留换行和空格 */
  word-break: break-word;
}
.pagination-toolbar {
    margin-top: 20px;
    display: flex;
    justify-content: center;
}
</style>