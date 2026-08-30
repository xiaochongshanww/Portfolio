<template>
  <div class="system-settings">
    <AdminPageHeader title="系统设置" description="配置站点信息、内容行为和系统参数。" />

    <!-- 05 §23 Settings Pattern:Stacked Sections(不做 tabs/不做表格) -->
    <div class="settings-stack">
      <!-- 站点信息 -->
      <section class="card">
        <div class="card-head">
          <h2>站点信息</h2>
          <el-button type="primary" size="small" :loading="savingGeneral" @click="saveGeneralSettings">
            保存更改
          </el-button>
        </div>
        <div class="card-body">
          <el-form ref="generalFormRef" :model="generalSettings" label-position="top" class="settings-form">
            <div class="form-grid">
              <el-form-item label="站点名称" prop="siteName">
                <el-input v-model="generalSettings.siteName" />
              </el-form-item>
              <el-form-item label="管理员邮箱" prop="adminEmail">
                <el-input v-model="generalSettings.adminEmail" />
              </el-form-item>
            </div>
            <el-form-item label="网站标语" prop="siteSlogan">
              <el-input v-model="generalSettings.siteSlogan" />
            </el-form-item>
            <el-form-item label="网站描述" prop="siteDescription">
              <el-input v-model="generalSettings.siteDescription" type="textarea" :rows="2" />
            </el-form-item>
            <div class="form-grid">
              <el-form-item label="默认语言" prop="defaultLanguage">
                <el-select v-model="generalSettings.defaultLanguage" class="w320">
                  <el-option label="简体中文" value="zh" />
                  <el-option label="English" value="en" />
                </el-select>
              </el-form-item>
              <el-form-item label="时区" prop="timezone">
                <el-select v-model="generalSettings.timezone" class="w320">
                  <el-option label="Asia/Shanghai" value="Asia/Shanghai" />
                  <el-option label="UTC" value="UTC" />
                </el-select>
              </el-form-item>
            </div>
          </el-form>
        </div>
      </section>

      <!-- 内容设置 -->
      <section class="card">
        <div class="card-head">
          <h2>内容设置</h2>
          <el-button type="primary" size="small" :loading="savingContent" @click="saveContentSettings">
            保存更改
          </el-button>
        </div>
        <div class="card-body">
          <el-form ref="contentFormRef" :model="contentSettings" label-position="top" class="settings-form">
            <div class="form-grid">
              <el-form-item label="每页文章数量" prop="articlesPerPage">
                <el-input-number v-model="contentSettings.articlesPerPage" :min="5" :max="100" />
              </el-form-item>
              <el-form-item label="默认文章状态" prop="defaultArticleStatus">
                <el-select v-model="contentSettings.defaultArticleStatus" class="w320">
                  <el-option label="草稿" value="draft" />
                  <el-option label="待审核" value="pending" />
                </el-select>
              </el-form-item>
            </div>
            <div class="form-grid">
              <el-form-item label="评论审核模式" prop="commentModeration">
                <el-select v-model="contentSettings.commentModeration" class="w320">
                  <el-option label="自动通过" value="auto" />
                  <el-option label="需要审核" value="manual" />
                </el-select>
              </el-form-item>
              <el-form-item label="文章摘要长度" prop="excerptLength">
                <el-input-number v-model="contentSettings.excerptLength" :min="50" :max="1000" />
              </el-form-item>
            </div>
            <div class="switch-row">
              <el-switch v-model="contentSettings.allowAnonymousComments" />
              <span>允许匿名评论</span>
            </div>
            <div class="switch-row">
              <el-switch v-model="contentSettings.enableArticleLikes" />
              <span>启用文章点赞</span>
            </div>
          </el-form>
        </div>
      </section>

      <!-- 安全设置 -->
      <section class="card">
        <div class="card-head">
          <h2>安全设置</h2>
          <el-button type="primary" size="small" :loading="savingSecurity" @click="saveSecuritySettings">
            保存更改
          </el-button>
        </div>
        <div class="card-body">
          <el-form ref="securityFormRef" :model="securitySettings" label-position="top" class="settings-form">
            <div class="form-grid">
              <el-form-item label="登录失败限制次数" prop="maxLoginAttempts">
                <el-input-number v-model="securitySettings.maxLoginAttempts" :min="3" :max="10" />
              </el-form-item>
              <el-form-item label="账户锁定时间(分钟)" prop="lockoutDuration">
                <el-input-number v-model="securitySettings.lockoutDuration" :min="5" :max="1440" />
              </el-form-item>
            </div>
            <div class="form-grid">
              <el-form-item label="JWT 令牌有效期(分钟)" prop="jwtExpiry">
                <el-input-number v-model="securitySettings.jwtExpiry" :min="5" :max="1440" />
              </el-form-item>
              <el-form-item label="最小密码长度" prop="minPasswordLength">
                <el-input-number v-model="securitySettings.minPasswordLength" :min="6" :max="32" />
              </el-form-item>
            </div>
            <el-form-item label="密码复杂度要求" prop="passwordComplexity">
              <el-checkbox-group v-model="securitySettings.passwordComplexity">
                <el-checkbox value="lowercase">小写字母</el-checkbox>
                <el-checkbox value="uppercase">大写字母</el-checkbox>
                <el-checkbox value="numbers">数字</el-checkbox>
                <el-checkbox value="symbols">特殊字符</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <div class="switch-row">
              <el-switch v-model="securitySettings.enableTwoFactor" />
              <span>启用双因子认证</span>
            </div>
            <div class="switch-row">
              <el-switch v-model="securitySettings.enableIpWhitelist" />
              <span>后台 IP 白名单</span>
            </div>
          </el-form>
        </div>
      </section>

      <!-- 系统维护(危险操作区,05 §26:危险按钮克制) -->
      <section class="card danger-card">
        <div class="card-head">
          <h2>系统维护</h2>
          <span class="head-note">以下操作立即生效,请谨慎执行</span>
        </div>
        <div class="card-body">
          <div class="kv-list">
            <div class="kv-row">
              <label>优化数据库</label>
              <div class="kv-action">
                <span class="kv-desc">重建索引与统计信息</span>
                <el-button size="small" :loading="dbOptimizing" @click="optimizeDatabase">执行</el-button>
              </div>
            </div>
            <div class="kv-row">
              <label>清理缓存</label>
              <div class="kv-action">
                <span class="kv-desc">清除应用层缓存</span>
                <el-button size="small" :loading="cacheClearing" @click="clearCache">立即清理</el-button>
              </div>
            </div>
            <div class="kv-row">
              <label>清理日志</label>
              <div class="kv-action">
                <span class="kv-desc">删除过期日志记录</span>
                <el-button size="small" :loading="logsCleaning" @click="cleanupLogsAction">立即清理</el-button>
              </div>
            </div>
            <div class="kv-row">
              <label>生成站点地图</label>
              <div class="kv-action">
                <span class="kv-desc">重新生成 sitemap.xml</span>
                <el-button size="small" :loading="sitemapGenerating" @click="generateSitemap">重新构建</el-button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
/**
 * 系统设置(05 §23 Settings Sections Pattern)
 * 数据面:设置保存此前为演示模式(接口注释未启用),本版沿用现状并预留
 * API.getSettings/updateSettings 的接线路径;维护操作里 clear-cache/sitemap 有真实端点。
 */
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { API } from '../../api';
import AdminPageHeader from '../../components/admin/AdminPageHeader.vue';

const loading = ref(false);
const savingGeneral = ref(false);
const savingContent = ref(false);
const savingSecurity = ref(false);
const dbOptimizing = ref(false);
const cacheClearing = ref(false);
const logsCleaning = ref(false);
const sitemapGenerating = ref(false);

/** @type {import('vue').Ref<any>} */
const generalFormRef = ref();
/** @type {import('vue').Ref<any>} */
const contentFormRef = ref();
/** @type {import('vue').Ref<any>} */
const securityFormRef = ref();

const generalSettings = reactive({
  siteName: '小重山',
  siteSlogan: '分享知识，记录思考',
  siteDescription: '个人技术主页:Python · AI · 软件工程 · 产品实践。',
  adminEmail: 'admin@example.com',
  contactPhone: '',
  defaultLanguage: 'zh',
  timezone: 'Asia/Shanghai',
});

const contentSettings = reactive({
  articlesPerPage: 10,
  commentModeration: 'auto',
  allowAnonymousComments: false,
  enableArticleLikes: true,
  defaultArticleStatus: 'draft',
  excerptLength: 200,
});

const securitySettings = reactive({
  maxLoginAttempts: 5,
  lockoutDuration: 15,
  jwtExpiry: 30,
  enableTwoFactor: false,
  passwordComplexity: ['lowercase', 'numbers'],
  minPasswordLength: 8,
  enableIpWhitelist: false,
});

/** @param {import('vue').ComponentPublicInstance | null} formRef @param {string} label @param {()=>Promise<any>} saveFn @param {{value:boolean}} saving */
/**
 * @param {{ validate: () => Promise<void> } | null} formRef
 * @param {string} label
 * @param {() => Promise<any>} saveFn
 * @param {{ value: boolean }} saving
 */
async function saveSection(formRef, label, saveFn, saving) {
  if (formRef) {
    try {
      await formRef.validate();
    } catch (e) {
      return;
    }
  }
  saving.value = true;
  try {
    await saveFn();
    ElMessage.success(`${label}保存成功`);
  } catch (e) {
    ElMessage.error(`${label}保存失败`);
  } finally {
    saving.value = false;
  }
}

function saveGeneralSettings() {
  // TODO(设置接线): 后端 settings API 就绪后改为
  //   await API.updateSettings('general', generalSettings)
  saveSection(generalFormRef.value, '基本设置', async () => {
    await new Promise((r) => setTimeout(r, 400));
  }, savingGeneral);
}

function saveContentSettings() {
  saveSection(contentFormRef.value, '内容设置', async () => {
    await new Promise((r) => setTimeout(r, 400));
  }, savingContent);
}

function saveSecuritySettings() {
  saveSection(securityFormRef.value, '安全设置', async () => {
    await new Promise((r) => setTimeout(r, 400));
  }, savingSecurity);
}

async function optimizeDatabase() {
  dbOptimizing.value = true;
  try {
    await new Promise((r) => setTimeout(r, 1200));
    ElMessage.success('数据库优化完成');
  } finally {
    dbOptimizing.value = false;
  }
}

async function clearCache() {
  cacheClearing.value = true;
  try {
    await API.clearCache();
    ElMessage.success('缓存清理完成');
  } catch (e) {
    ElMessage.error('缓存清理失败');
  } finally {
    cacheClearing.value = false;
  }
}

async function cleanupLogsAction() {
  logsCleaning.value = true;
  try {
    await new Promise((r) => setTimeout(r, 800));
    ElMessage.success('日志清理完成');
  } finally {
    logsCleaning.value = false;
  }
}

async function generateSitemap() {
  sitemapGenerating.value = true;
  try {
    await API.generateSitemap();
    ElMessage.success('站点地图已生成');
  } catch (e) {
    ElMessage.error('站点地图生成失败');
  } finally {
    sitemapGenerating.value = false;
  }
}

onMounted(() => {
  // TODO(设置接线): API.getSettings('all') 回填三个 section
  loading.value = false;
});
</script>

<style scoped>
.system-settings {
  width: 100%;
}
.settings-stack {
  display: grid;
  gap: 16px;
}
.card {
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-r-container);
  background: var(--adm-surface);
}
.card-head {
  padding: 14px 16px;
  border-bottom: 1px solid var(--adm-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.card-head h2 {
  font-size: 14px;
  margin: 0;
  color: var(--adm-text);
}
.head-note {
  font-size: 12px;
  color: var(--adm-muted-light);
}
.card-body {
  padding: 16px;
}

.settings-form :deep(.el-form-item) {
  margin-bottom: 14px;
}
.settings-form :deep(.el-form-item__label) {
  font-size: 12px;
  color: var(--adm-muted);
  padding-bottom: 4px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 24px;
}
.w320 {
  width: 320px;
  max-width: 100%;
}
.switch-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  font-size: 13px;
  color: var(--adm-text-2);
}

/* 维护区(05 §26:危险区用软色提示,不整片染红) */
.danger-card {
  border-color: #fecaca;
}
.danger-card .card-head {
  background: #fff7f7;
}
.kv-list {
  display: grid;
}
.kv-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid var(--adm-border);
  align-items: center;
}
.kv-row:first-child {
  border-top: 0;
  padding-top: 2px;
}
.kv-row label {
  font-size: 12px;
  color: var(--adm-muted);
}
.kv-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.kv-desc {
  font-size: 12px;
  color: var(--adm-text-2);
}

@media (max-width: 800px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .kv-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }
}
</style>
