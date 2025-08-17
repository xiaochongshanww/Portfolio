<template>
  <div class="metrics-dashboard-page">
    <h1>站点数据看板</h1>
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>
    <div v-else-if="error" class="error-container">
      <el-alert title="加载数据失败" type="error" :description="error" show-icon :closable="false"></el-alert>
    </div>
    <div v-else class="stats-grid">
      <!-- Articles -->
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>文章统计</span>
          </div>
        </template>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="总数" :value="stats.articles.total" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="已发布" :value="stats.articles.published" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="草稿" :value="stats.articles.draft" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="待审核" :value="stats.articles.pending">
              <template #suffix>
                <el-icon v-if="stats.articles.pending > 0" style="color: #E6A23C"><Warning /></el-icon>
              </template>
            </el-statistic>
          </el-col>
        </el-row>
      </el-card>

      <!-- Comments -->
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>评论统计</span>
          </div>
        </template>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="总数" :value="stats.comments.total" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="已批准" :value="stats.comments.approved" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="待审核" :value="stats.comments.pending">
               <template #suffix>
                <el-icon v-if="stats.comments.pending > 0" style="color: #E6A23C"><Warning /></el-icon>
              </template>
            </el-statistic>
          </el-col>
        </el-row>
      </el-card>

      <!-- Users -->
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>用户统计</span>
          </div>
        </template>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="总用户数" :value="stats.users.total" />
          </el-col>
        </el-row>
      </el-card>

      <!-- Taxonomy -->
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>分类与标签</span>
          </div>
        </template>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-statistic title="分类总数" :value="stats.taxonomy.categories" />
          </el-col>
          <el-col :span="12">
            <el-statistic title="标签总数" :value="stats.taxonomy.tags" />
          </el-col>
        </el-row>
      </el-card>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage, ElStatistic, ElCard, ElRow, ElCol, ElAlert, ElSkeleton, ElIcon } from 'element-plus';
import { Warning } from '@element-plus/icons-vue';
import apiClient from '../apiClient';

const loading = ref(true);
const error = ref(null);
const stats = ref({
  articles: { total: 0, published: 0, draft: 0, pending: 0 },
  comments: { total: 0, pending: 0, approved: 0 },
  users: { total: 0 },
  taxonomy: { tags: 0, categories: 0 },
});

const api = {
  getSummary: () => apiClient.get('/metrics/summary'),
};

const fetchStats = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await api.getSummary();
    stats.value = response.data.data;
  } catch (err) {
    error.value = err.response?.data?.message || '无法连接到服务器';
    ElMessage.error('加载统计数据失败');
    console.error(err);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchStats();
});
</script>

<style scoped>
.metrics-dashboard-page {
  padding: 20px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
.el-statistic {
  text-align: center;
}
.loading-container, .error-container {
    padding: 20px;
}
.el-row .el-col {
    margin-bottom: 20px;
}
</style>