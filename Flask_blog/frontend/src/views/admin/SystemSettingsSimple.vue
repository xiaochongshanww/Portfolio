<template>
  <div class="system-settings">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <h2>系统设置</h2>
          <span class="settings-desc">管理系统配置和参数</span>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="settings-tabs">
        <!-- 基本设置 -->
        <el-tab-pane label="基本设置" name="general">
          <div class="tab-content">
            <el-form :model="generalSettings" label-width="120px" size="default">
              <el-form-item label="网站标题">
                <el-input v-model="generalSettings.siteName" placeholder="输入网站标题" />
              </el-form-item>
              
              <el-form-item label="网站描述">
                <el-input
                  v-model="generalSettings.siteDescription"
                  type="textarea"
                  :rows="3"
                  placeholder="输入网站描述"
                />
              </el-form-item>
              
              <el-form-item label="管理员邮箱">
                <el-input v-model="generalSettings.adminEmail" placeholder="输入管理员邮箱" />
              </el-form-item>
              
              <el-form-item>
                <el-button type="primary" @click="saveSettings" :loading="saving">
                  保存设置
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- 系统信息 -->
        <el-tab-pane label="系统信息" name="info">
          <div class="tab-content">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="系统版本">1.0.0</el-descriptions-item>
              <el-descriptions-item label="运行状态">正常</el-descriptions-item>
              <el-descriptions-item label="数据库">正常</el-descriptions-item>
              <el-descriptions-item label="缓存">正常</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { ElMessage } from 'element-plus';

const activeTab = ref('general');
const saving = ref(false);

const generalSettings = reactive({
  siteName: 'Flask Blog',
  siteDescription: '一个基于Flask的博客系统',
  adminEmail: 'admin@example.com'
});

const saveSettings = async () => {
  saving.value = true;
  
  // 模拟保存延迟
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  ElMessage.success('设置保存成功');
  saving.value = false;
};
</script>

<style scoped>
.system-settings {
  padding: 24px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.settings-card {
  margin: 0 auto;
  max-width: 800px;
}

.card-header {
  display: flex;
  flex-direction: column;
}

.card-header h2 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 20px;
}

.settings-desc {
  color: #909399;
  font-size: 14px;
}

.settings-tabs {
  margin-top: 20px;
}

.tab-content {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}
</style>