<template>
  <div class="system-settings">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">⚙️ 系统设置</h1>
        <p class="page-description">配置和管理系统的各项参数</p>
      </div>
      <div class="header-actions">
        <el-button @click="refreshSettings" :loading="loading" icon="Refresh">刷新</el-button>
        <el-button @click="exportSettings" type="primary" icon="Download">
          导出配置
        </el-button>
      </div>
    </div>

    <!-- 设置导航标签页 -->
    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- 基本设置 -->
      <el-tab-pane label="基本设置" name="general">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <span>网站基本信息</span>
              <el-button @click="saveGeneralSettings" :loading="savingGeneral" type="primary" size="small">
                保存设置
              </el-button>
            </div>
          </template>
          
          <el-form :model="generalSettings" :rules="generalRules" ref="generalFormRef" label-width="120px">
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="网站名称" prop="siteName">
                  <el-input v-model="generalSettings.siteName" placeholder="请输入网站名称" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="网站标语" prop="siteSlogan">
                  <el-input v-model="generalSettings.siteSlogan" placeholder="请输入网站标语" />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="网站描述" prop="siteDescription">
              <el-input 
                v-model="generalSettings.siteDescription" 
                type="textarea" 
                :rows="3"
                placeholder="请输入网站描述，用于SEO优化"
              />
            </el-form-item>
            
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="管理员邮箱" prop="adminEmail">
                  <el-input v-model="generalSettings.adminEmail" placeholder="请输入管理员邮箱" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="联系电话" prop="contactPhone">
                  <el-input v-model="generalSettings.contactPhone" placeholder="请输入联系电话" />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="默认语言" prop="defaultLanguage">
                  <el-select v-model="generalSettings.defaultLanguage" style="width: 100%">
                    <el-option label="中文" value="zh" />
                    <el-option label="English" value="en" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="时区设置" prop="timezone">
                  <el-select v-model="generalSettings.timezone" style="width: 100%">
                    <el-option label="Asia/Shanghai" value="Asia/Shanghai" />
                    <el-option label="UTC" value="UTC" />
                    <el-option label="America/New_York" value="America/New_York" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 内容设置 -->
      <el-tab-pane label="内容设置" name="content">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <span>内容发布与管理</span>
              <el-button @click="saveContentSettings" :loading="savingContent" type="primary" size="small">
                保存设置
              </el-button>
            </div>
          </template>
          
          <el-form :model="contentSettings" :rules="contentRules" ref="contentFormRef" label-width="140px">
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="每页文章数量" prop="articlesPerPage">
                  <el-input-number 
                    v-model="contentSettings.articlesPerPage" 
                    :min="1" 
                    :max="100" 
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="评论审核模式" prop="commentModeration">
                  <el-select v-model="contentSettings.commentModeration" style="width: 100%">
                    <el-option label="自动审核" value="auto" />
                    <el-option label="人工审核" value="manual" />
                    <el-option label="关闭评论" value="disabled" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="允许匿名评论" prop="allowAnonymousComments">
                  <el-switch v-model="contentSettings.allowAnonymousComments" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="启用文章点赞" prop="enableArticleLikes">
                  <el-switch v-model="contentSettings.enableArticleLikes" />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="默认文章状态" prop="defaultArticleStatus">
              <el-radio-group v-model="contentSettings.defaultArticleStatus">
                <el-radio label="draft">草稿</el-radio>
                <el-radio label="published">发布</el-radio>
                <el-radio label="scheduled">定时发布</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="文章摘要长度" prop="excerptLength">
              <el-input-number 
                v-model="contentSettings.excerptLength" 
                :min="50" 
                :max="500" 
                style="width: 200px"
              />
              <span class="form-hint">字符（用于自动生成摘要）</span>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 安全设置 -->
      <el-tab-pane label="安全设置" name="security">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <span>系统安全配置</span>
              <el-button @click="saveSecuritySettings" :loading="savingSecurity" type="primary" size="small">
                保存设置
              </el-button>
            </div>
          </template>
          
          <el-form :model="securitySettings" :rules="securityRules" ref="securityFormRef" label-width="160px">
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="登录失败限制次数" prop="maxLoginAttempts">
                  <el-input-number 
                    v-model="securitySettings.maxLoginAttempts" 
                    :min="3" 
                    :max="20" 
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="账户锁定时间" prop="lockoutDuration">
                  <el-input-number 
                    v-model="securitySettings.lockoutDuration" 
                    :min="5" 
                    :max="1440" 
                    style="width: 100%"
                  />
                  <span class="form-hint">分钟</span>
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="JWT令牌有效期" prop="jwtExpiry">
                  <el-input-number 
                    v-model="securitySettings.jwtExpiry" 
                    :min="30" 
                    :max="1440" 
                    style="width: 100%"
                  />
                  <span class="form-hint">分钟</span>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="启用双因子认证" prop="enableTwoFactor">
                  <el-switch v-model="securitySettings.enableTwoFactor" />
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="密码复杂度要求" prop="passwordComplexity">
              <el-checkbox-group v-model="securitySettings.passwordComplexity">
                <el-checkbox label="lowercase">包含小写字母</el-checkbox>
                <el-checkbox label="uppercase">包含大写字母</el-checkbox>
                <el-checkbox label="numbers">包含数字</el-checkbox>
                <el-checkbox label="symbols">包含特殊字符</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="最小密码长度" prop="minPasswordLength">
                  <el-input-number 
                    v-model="securitySettings.minPasswordLength" 
                    :min="6" 
                    :max="50" 
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="启用IP白名单" prop="enableIpWhitelist">
                  <el-switch v-model="securitySettings.enableIpWhitelist" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 系统维护 -->
      <el-tab-pane label="系统维护" name="maintenance">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <span>系统维护与优化</span>
            </div>
          </template>
          
          <div class="maintenance-section">
            <h3>数据库维护</h3>
            <el-row :gutter="16" class="maintenance-actions">
              <el-col :span="6">
                <el-button @click="optimizeDatabase" :loading="dbOptimizing" type="primary" block>
                  <el-icon><Setting /></el-icon>
                  优化数据库
                </el-button>
              </el-col>
              <el-col :span="6">
                <el-button @click="clearCache" :loading="cacheClearing" type="warning" block>
                  <el-icon><Delete /></el-icon>
                  清理缓存
                </el-button>
              </el-col>
              <el-col :span="6">
                <el-button @click="cleanupLogs" :loading="logsCleaning" type="info" block>
                  <el-icon><Document /></el-icon>
                  清理日志
                </el-button>
              </el-col>
              <el-col :span="6">
                <el-button @click="generateSitemap" :loading="sitemapGenerating" type="success" block>
                  <el-icon><Folder /></el-icon>
                  生成站点地图
                </el-button>
              </el-col>
            </el-row>
          </div>

          <div class="maintenance-section">
            <h3>系统信息</h3>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="系统版本">
                {{ systemInfo.version }}
              </el-descriptions-item>
              <el-descriptions-item label="运行时间">
                {{ systemInfo.uptime }}
              </el-descriptions-item>
              <el-descriptions-item label="数据库大小">
                {{ systemInfo.dbSize }}
              </el-descriptions-item>
              <el-descriptions-item label="缓存使用">
                {{ systemInfo.cacheUsage }}
              </el-descriptions-item>
              <el-descriptions-item label="总文章数">
                {{ systemInfo.totalArticles }}
              </el-descriptions-item>
              <el-descriptions-item label="总用户数">
                {{ systemInfo.totalUsers }}
              </el-descriptions-item>
              <el-descriptions-item label="磁盘使用">
                {{ systemInfo.diskUsage }}
              </el-descriptions-item>
              <el-descriptions-item label="最后备份">
                {{ systemInfo.lastBackup }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="maintenance-section">
            <h3>备份与恢复</h3>
            <el-row :gutter="16" class="maintenance-actions">
              <el-col :span="8">
                <el-button @click="createBackup" :loading="backupCreating" type="primary" block>
                  <el-icon><FolderAdd /></el-icon>
                  创建备份
                </el-button>
              </el-col>
              <el-col :span="8">
                <el-upload
                  class="backup-upload"
                  :auto-upload="false"
                  :on-change="handleBackupFile"
                  accept=".zip,.sql"
                >
                  <el-button type="success" block>
                    <el-icon><Upload /></el-icon>
                    上传备份
                  </el-button>
                </el-upload>
              </el-col>
              <el-col :span="8">
                <el-button @click="showBackupHistory" type="info" block>
                  <el-icon><Clock /></el-icon>
                  备份历史
                </el-button>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 备份历史对话框 -->
    <el-dialog v-model="backupHistoryVisible" title="备份历史" width="60%">
      <el-table :data="backupHistory" style="width: 100%">
        <el-table-column prop="filename" label="备份文件名" min-width="200" />
        <el-table-column prop="size" label="文件大小" width="120" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="{row}">
            <el-button @click="downloadBackup(row)" type="text" size="small">下载</el-button>
            <el-button @click="deleteBackup(row)" type="text" size="small" class="delete-btn">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  Refresh, Download, Setting, Delete, Document, Folder, 
  FolderAdd, Upload, Clock 
} from '@element-plus/icons-vue';
// 暂时注释apiClient导入，使用静态数据
// import api from '../../apiClient';

// 响应式数据
const loading = ref(false);
const activeTab = ref('general');
const savingGeneral = ref(false);
const savingContent = ref(false);
const savingSecurity = ref(false);
const dbOptimizing = ref(false);
const cacheClearing = ref(false);
const logsCleaning = ref(false);
const sitemapGenerating = ref(false);
const backupCreating = ref(false);
const backupHistoryVisible = ref(false);

const generalFormRef = ref(null);
const contentFormRef = ref(null);
const securityFormRef = ref(null);

// 基本设置
const generalSettings = reactive({
  siteName: 'Flask博客系统',
  siteSlogan: '分享知识，记录思考',
  siteDescription: '一个基于Flask开发的现代化博客系统，支持Markdown编辑、分类管理、评论系统等功能。',
  adminEmail: 'admin@example.com',
  contactPhone: '',
  defaultLanguage: 'zh',
  timezone: 'Asia/Shanghai'
});

// 内容设置
const contentSettings = reactive({
  articlesPerPage: 10,
  commentModeration: 'auto',
  allowAnonymousComments: false,
  enableArticleLikes: true,
  defaultArticleStatus: 'draft',
  excerptLength: 200
});

// 安全设置
const securitySettings = reactive({
  maxLoginAttempts: 5,
  lockoutDuration: 15,
  jwtExpiry: 30,
  enableTwoFactor: false,
  passwordComplexity: ['lowercase', 'numbers'],
  minPasswordLength: 8,
  enableIpWhitelist: false
});

// 系统信息
const systemInfo = reactive({
  version: '1.0.0',
  uptime: '7天 12小时',
  dbSize: '45.6 MB',
  cacheUsage: '12.3 MB',
  totalArticles: 128,
  totalUsers: 42,
  diskUsage: '2.1 GB / 10 GB',
  lastBackup: '2024-01-15 10:30:00'
});

// 备份历史
const backupHistory = ref([
  {
    filename: 'backup_2024_01_15_103000.zip',
    size: '15.2 MB',
    createTime: '2024-01-15 10:30:00'
  },
  {
    filename: 'backup_2024_01_14_103000.zip',
    size: '14.8 MB', 
    createTime: '2024-01-14 10:30:00'
  }
]);

// 表单验证规则
const generalRules = {
  siteName: [
    { required: true, message: '请输入网站名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  adminEmail: [
    { required: true, message: '请输入管理员邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
};

const contentRules = {
  articlesPerPage: [
    { required: true, message: '请设置每页文章数量', trigger: 'blur' }
  ]
};

const securityRules = {
  maxLoginAttempts: [
    { required: true, message: '请设置登录失败限制次数', trigger: 'blur' }
  ],
  minPasswordLength: [
    { required: true, message: '请设置最小密码长度', trigger: 'blur' }
  ]
};

// 加载设置数据
const loadSettings = async () => {
  try {
    loading.value = true;
    
    // 模拟加载配置数据
    // const response = await api.get('/system/settings');
    // if (response.data.code === 0) {
    //   Object.assign(generalSettings, response.data.data.general);
    //   Object.assign(contentSettings, response.data.data.content);
    //   Object.assign(securitySettings, response.data.data.security);
    // }
    
    // 模拟加载系统信息
    // const infoResponse = await api.get('/system/info');
    // if (infoResponse.data.code === 0) {
    //   Object.assign(systemInfo, infoResponse.data.data);
    // }
    
    console.log('Settings loaded successfully');
    ElMessage.success('设置加载成功');
  } catch (error) {
    console.error('加载设置失败:', error);
    ElMessage.error('加载设置失败');
  } finally {
    loading.value = false;
  }
};

// 保存基本设置
const saveGeneralSettings = async () => {
  if (!generalFormRef.value) return;
  
  try {
    await generalFormRef.value.validate();
    savingGeneral.value = true;
    
    // const response = await api.put('/system/settings/general', generalSettings);
    // if (response.data.code === 0) {
    //   ElMessage.success('基本设置保存成功');
    // }
    
    // 演示模式
    setTimeout(() => {
      ElMessage.success('基本设置保存成功（演示模式）');
      savingGeneral.value = false;
    }, 1000);
    
  } catch (error) {
    if (error !== 'validation failed') {
      console.error('保存基本设置失败:', error);
      ElMessage.error('保存设置失败');
      savingGeneral.value = false;
    }
  }
};

// 保存内容设置
const saveContentSettings = async () => {
  if (!contentFormRef.value) return;
  
  try {
    await contentFormRef.value.validate();
    savingContent.value = true;
    
    setTimeout(() => {
      ElMessage.success('内容设置保存成功（演示模式）');
      savingContent.value = false;
    }, 1000);
    
  } catch (error) {
    if (error !== 'validation failed') {
      console.error('保存内容设置失败:', error);
      ElMessage.error('保存设置失败');
      savingContent.value = false;
    }
  }
};

// 保存安全设置
const saveSecuritySettings = async () => {
  if (!securityFormRef.value) return;
  
  try {
    await securityFormRef.value.validate();
    savingSecurity.value = true;
    
    setTimeout(() => {
      ElMessage.success('安全设置保存成功（演示模式）');
      savingSecurity.value = false;
    }, 1000);
    
  } catch (error) {
    if (error !== 'validation failed') {
      console.error('保存安全设置失败:', error);
      ElMessage.error('保存设置失败');
      savingSecurity.value = false;
    }
  }
};

// 系统维护操作
const optimizeDatabase = async () => {
  try {
    await ElMessageBox.confirm('确定要优化数据库吗？此操作可能需要几分钟时间。', '确认优化', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    dbOptimizing.value = true;
    
    setTimeout(() => {
      ElMessage.success('数据库优化完成');
      dbOptimizing.value = false;
    }, 3000);
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('优化数据库失败:', error);
      ElMessage.error('优化数据库失败');
    }
  }
};

const clearCache = async () => {
  try {
    cacheClearing.value = true;
    
    setTimeout(() => {
      ElMessage.success('缓存清理完成');
      cacheClearing.value = false;
    }, 1500);
    
  } catch (error) {
    console.error('清理缓存失败:', error);
    ElMessage.error('清理缓存失败');
  }
};

const cleanupLogs = async () => {
  try {
    logsCleaning.value = true;
    
    setTimeout(() => {
      ElMessage.success('日志清理完成');
      logsCleaning.value = false;
    }, 2000);
    
  } catch (error) {
    console.error('清理日志失败:', error);
    ElMessage.error('清理日志失败');
  }
};

const generateSitemap = async () => {
  try {
    sitemapGenerating.value = true;
    
    setTimeout(() => {
      ElMessage.success('站点地图生成完成');
      sitemapGenerating.value = false;
    }, 2000);
    
  } catch (error) {
    console.error('生成站点地图失败:', error);
    ElMessage.error('生成站点地图失败');
  }
};

// 备份相关操作
const createBackup = async () => {
  try {
    await ElMessageBox.confirm('确定要创建系统备份吗？', '确认备份', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    });
    
    backupCreating.value = true;
    
    setTimeout(() => {
      const now = new Date();
      const filename = `backup_${now.getFullYear()}_${(now.getMonth() + 1).toString().padStart(2, '0')}_${now.getDate().toString().padStart(2, '0')}_${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}${now.getSeconds().toString().padStart(2, '0')}.zip`;
      
      backupHistory.value.unshift({
        filename,
        size: '16.7 MB',
        createTime: now.toLocaleString()
      });
      
      ElMessage.success('备份创建完成');
      backupCreating.value = false;
    }, 4000);
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('创建备份失败:', error);
      ElMessage.error('创建备份失败');
    }
  }
};

const handleBackupFile = (file: any) => {
  ElMessage.info('备份文件上传功能开发中');
};

const showBackupHistory = () => {
  backupHistoryVisible.value = true;
};

const downloadBackup = (backup: any) => {
  ElMessage.success(`开始下载备份文件: ${backup.filename}`);
};

const deleteBackup = async (backup: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除备份文件 "${backup.filename}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });
    
    const index = backupHistory.value.findIndex(item => item.filename === backup.filename);
    if (index > -1) {
      backupHistory.value.splice(index, 1);
      ElMessage.success('备份文件删除成功');
    }
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除备份失败:', error);
      ElMessage.error('删除备份失败');
    }
  }
};

// 刷新设置
const refreshSettings = () => {
  loadSettings();
};

// 导出配置
const exportSettings = () => {
  const config = {
    general: generalSettings,
    content: contentSettings,
    security: securitySettings,
    exportTime: new Date().toISOString()
  };
  
  const dataStr = JSON.stringify(config, null, 2);
  const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
  
  const exportFileDefaultName = `system_settings_${new Date().toISOString().slice(0, 10)}.json`;
  
  const linkElement = document.createElement('a');
  linkElement.setAttribute('href', dataUri);
  linkElement.setAttribute('download', exportFileDefaultName);
  linkElement.click();
  
  ElMessage.success('配置导出成功');
};

// 生命周期
onMounted(async () => {
  console.log('SystemSettings component mounted');
  try {
    await loadSettings();
    console.log('SystemSettings data loaded successfully');
  } catch (error) {
    console.error('SystemSettings loading error:', error);
  }
});
</script>

<style scoped>
.system-settings {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
}

.page-description {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.settings-tabs {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.settings-card {
  margin-bottom: 24px;
  box-shadow: none;
  border: 1px solid #e5e7eb;
}

.settings-card:last-child {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-hint {
  margin-left: 8px;
  color: #6b7280;
  font-size: 14px;
}

.maintenance-section {
  margin-bottom: 32px;
}

.maintenance-section:last-child {
  margin-bottom: 0;
}

.maintenance-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.maintenance-actions {
  margin-bottom: 24px;
}

.backup-upload {
  width: 100%;
}

.backup-upload :deep(.el-upload) {
  width: 100%;
}

.delete-btn {
  color: #f56c6c;
}

.delete-btn:hover {
  color: #f56c6c;
  background-color: #fef0f0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .settings-tabs {
    padding: 16px;
  }
  
  .maintenance-actions :deep(.el-col) {
    margin-bottom: 12px;
  }
}
</style>