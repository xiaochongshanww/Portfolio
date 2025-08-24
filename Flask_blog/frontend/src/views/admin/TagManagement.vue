<template>
  <div class="tag-management">
    <!-- 现代化页面头部 -->
    <div class="modern-page-header">
      <div class="page-header">
        <div class="title-container">
          <div class="title-icon">
            <el-icon size="28"><Document /></el-icon>
          </div>
          <div class="header-content">
            <h1 class="page-title">标签管理</h1>
            <p class="page-description">管理文章标签，提升内容可发现性</p>
          </div>
        </div>
        <div class="header-actions">
          <button @click="loadData" :disabled="loading" class="action-btn secondary">
            <el-icon size="16" :class="{ 'is-loading': loading }"><Refresh /></el-icon>
            <span>刷新</span>
          </button>
          <button 
            @click="cleanUnusedTags"
            :disabled="stats.unused_tags === 0" 
            class="action-btn danger"
          >
            <el-icon size="16"><Delete /></el-icon>
            <span>清理未使用 ({{ stats.unused_tags }})</span>
          </button>
          <button @click="showCreateDialog" class="action-btn primary">
            <el-icon size="16"><Plus /></el-icon>
            <span>新建标签</span>
          </button>
        </div>
      </div>
      
      <!-- 统计面板 -->
      <div class="modern-stats">
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><DataBoard /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">总标签</span>
              <span class="stat-value">{{ stats.total_tags }}</span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">已使用</span>
              <span class="stat-value active">{{ stats.tags_with_articles }}</span>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-header">
            <div class="stat-icon">
              <el-icon size="20"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">未使用</span>
              <span class="stat-value unused">{{ stats.unused_tags }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 现代化筛选器 -->
    <div class="modern-filter-container">
      <div class="filter-row">
        <div class="filter-group">
          <div class="modern-search-input">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索标签名称..."
              clearable
              @input="handleSearch"
              class="search-input"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
          
          <div class="modern-select">
            <el-select v-model="sortBy" placeholder="排序方式" @change="handleSort" class="sort-select">
              <el-option label="按使用量降序" value="usage_desc" />
              <el-option label="按使用量升序" value="usage_asc" />
              <el-option label="按名称A-Z" value="name_asc" />
              <el-option label="按名称Z-A" value="name_desc" />
              <el-option label="按创建时间" value="created_desc" />
            </el-select>
          </div>
        </div>
        
        <div class="modern-view-toggle">
          <el-radio-group v-model="viewMode" @change="handleViewModeChange" class="view-mode-selector">
            <el-radio-button label="table">表格视图</el-radio-button>
            <el-radio-button label="cloud">标签云</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </div>

    <!-- 现代化表格视图 -->
    <div v-if="viewMode === 'table'" class="modern-tags-table">
      <el-table
        v-loading="loading"
        :data="filteredTags"
        @selection-change="handleSelectionChange"
        size="default"
        class="modern-table"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="name" label="标签名称" min-width="200">
          <template #default="{ row }">
            <div class="modern-tag-name">
              <div class="tag-badge" :class="getTagClass(row.article_count)">
                <el-icon size="14"><Document /></el-icon>
                <span class="tag-text">{{ row.name }}</span>
              </div>
              <div class="usage-info">
                <span class="usage-count">{{ row.article_count }} 次</span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="slug" label="Slug" width="200">
          <template #default="{ row }">
            <code class="slug-code">{{ row.slug }}</code>
          </template>
        </el-table-column>
        
        <el-table-column prop="article_count" label="使用情况" width="180" align="center" sortable>
          <template #default="{ row }">
            <div class="modern-usage-display">
              <div class="usage-progress">
                <div class="progress-bar">
                  <div 
                    class="progress-fill" 
                    :style="{ 
                      width: getUsagePercentage(row.article_count) + '%',
                      background: getProgressGradient(row.article_count)
                    }"
                  ></div>
                </div>
                <div class="usage-stats">
                  <span class="usage-number">{{ row.article_count }}</span>
                  <span class="usage-percentage">{{ getUsagePercentage(row.article_count) }}%</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="modern-action-buttons">
              <button
                @click="showEditDialog(row)"
                class="table-btn edit"
              >
                <el-icon size="14"><Edit /></el-icon>
                <span>编辑</span>
              </button>
              
              <button
                @click="handleDelete(row)"
                :disabled="row.article_count > 0"
                class="table-btn delete"
                :class="{ 'disabled': row.article_count > 0 }"
              >
                <el-icon size="14"><Delete /></el-icon>
                <span>删除</span>
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 现代化标签云视图 -->
    <div v-else class="modern-tag-cloud">
      <div class="cloud-container">
        <div 
          v-for="tag in filteredTags" 
          :key="tag.id"
          class="modern-cloud-tag"
          :class="{ 'unused': tag.article_count === 0 }"
          :style="getCloudTagStyle(tag)"
          @click="showEditDialog(tag)"
        >
          <span class="tag-text">{{ tag.name }}</span>
          <span class="tag-count">({{ tag.article_count }})</span>
        </div>
      </div>
    </div>

    <!-- 现代化空状态 -->
    <div v-if="!loading && tags.length === 0" class="modern-empty-state">
      <div class="empty-content">
        <div class="empty-icon">
          <el-icon size="80"><Document /></el-icon>
        </div>
        <h3 class="empty-title">暂无标签数据</h3>
        <p class="empty-description">您还没有创建任何标签，赶快创建您的第一个标签吧！</p>
        <button @click="showCreateDialog" class="empty-action-btn">
          <el-icon size="16"><Plus /></el-icon>
          <span>创建第一个标签</span>
        </button>
      </div>
    </div>

    <!-- 现代化创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建标签' : '编辑标签'"
      width="500px"
      @close="resetForm"
      class="modern-dialog"
      :show-close="false"
      align-center
    >
      <template #header>
        <div class="dialog-header">
          <div class="dialog-title">
            <el-icon size="24" class="dialog-icon"><Document /></el-icon>
            <span>{{ dialogMode === 'create' ? '新建标签' : '编辑标签' }}</span>
          </div>
          <button @click="dialogVisible = false" class="dialog-close">
            <el-icon size="18"><Close /></el-icon>
          </button>
        </div>
      </template>
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="80px"
      >
        <el-form-item label="标签名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入标签名称"
            @input="generateSlug"
          />
        </el-form-item>
        
        <el-form-item label="Slug" prop="slug">
          <el-input
            v-model="form.slug"
            placeholder="URL友好的标识符，留空自动生成"
          >
            <template #suffix>
              <el-tooltip 
                content="Slug用于URL中，只能包含小写字母、数字和连字符。中文标签名会自动转换为拼音。" 
                placement="top"
              >
                <el-icon class="slug-help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </template>
          </el-input>
          <div class="slug-preview" v-if="form.slug">
            <span class="preview-label">预览URL：</span>
            <code class="preview-url">/tag/{{ form.slug }}</code>
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="modern-dialog-footer">
          <button @click="dialogVisible = false" class="dialog-btn secondary">
            <span>取消</span>
          </button>
          <button
            @click="handleSubmit"
            :disabled="submitting"
            class="dialog-btn primary"
          >
            <el-icon v-if="submitting" size="16" class="loading-icon"><Refresh /></el-icon>
            <el-icon v-else size="16"><Check /></el-icon>
            <span>{{ dialogMode === 'create' ? '创建' : '保存' }}</span>
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Search, Edit, Delete, Refresh, Document, DataBoard, Close, Check, QuestionFilled } from '@element-plus/icons-vue';
import api from '../../apiClient';

// 响应式数据
const loading = ref(false);
const submitting = ref(false);
const dialogVisible = ref(false);
const dialogMode = ref('create');
const editingId = ref(null);
const searchKeyword = ref('');
const sortBy = ref('usage_desc');
const viewMode = ref('table');
const selectedTags = ref([]);

const tags = ref([]);
const formRef = ref();

// 统计数据
const stats = reactive({
  total_tags: 0,
  tags_with_articles: 0,
  unused_tags: 0
});

// 表单数据
const form = reactive({
  name: '',
  slug: ''
});

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入标签名称', trigger: 'blur' },
    { min: 1, max: 80, message: '长度在 1 到 80 个字符', trigger: 'blur' }
  ],
  slug: [
    { pattern: /^[a-z0-9-]*$/, message: 'Slug只能包含小写字母、数字和连字符', trigger: 'blur' }
  ]
};

// 计算属性：筛选后的标签
const filteredTags = computed(() => {
  let filtered = [...tags.value];
  
  // 搜索筛选
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase();
    filtered = filtered.filter(tag => 
      tag.name.toLowerCase().includes(keyword) ||
      tag.slug.toLowerCase().includes(keyword)
    );
  }
  
  // 排序
  filtered.sort((a, b) => {
    switch (sortBy.value) {
      case 'usage_desc':
        return b.article_count - a.article_count;
      case 'usage_asc':
        return a.article_count - b.article_count;
      case 'name_asc':
        return a.name.localeCompare(b.name);
      case 'name_desc':
        return b.name.localeCompare(a.name);
      case 'created_desc':
      default:
        return b.id - a.id;
    }
  });
  
  return filtered;
});

// 加载数据
const loadData = async () => {
  if (loading.value) return;
  
  try {
    loading.value = true;
    const response = await api.get('/taxonomy/stats');
    
    if (response.data.code === 0) {
      const data = response.data.data;
      tags.value = data.tags;
      Object.assign(stats, data.summary);
    } else {
      ElMessage.error(response.data.message || '加载数据失败');
    }
  } catch (error) {
    console.error('加载标签数据失败:', error);
    ElMessage.error('加载标签数据失败');
  } finally {
    loading.value = false;
  }
};

// 显示创建对话框
const showCreateDialog = () => {
  dialogMode.value = 'create';
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
};

// 显示编辑对话框
const showEditDialog = (tag) => {
  dialogMode.value = 'edit';
  editingId.value = tag.id;
  form.name = tag.name;
  form.slug = tag.slug;
  dialogVisible.value = true;
};

// 重置表单
const resetForm = () => {
  form.name = '';
  form.slug = '';
  if (formRef.value) {
    formRef.value.resetFields();
  }
};

// 根据名称生成Slug
const generateSlug = () => {
  if (!form.slug && form.name) {
    // 中文转拼音的简单映射（可以扩展）
    const chineseToPinyin = {
      '技术': 'jishu',
      '前端': 'qianduan', 
      '后端': 'houduan',
      '开发': 'kaifa',
      '编程': 'biancheng',
      '设计': 'sheji',
      '产品': 'chanpin',
      '运营': 'yunying',
      '数据': 'shuju',
      '算法': 'suanfa',
      '框架': 'kuangjia',
      '工具': 'gongju',
      '教程': 'jiaocheng',
      '入门': 'rumen',
      '进阶': 'jinjie',
      '实战': 'shizhan',
      '基础': 'jichu',
      '高级': 'gaoji',
      '最新': 'zuixin',
      '热门': 'remen'
    };
    
    let slug = form.name.toLowerCase();
    
    // 替换常见中文词汇为拼音
    Object.keys(chineseToPinyin).forEach(chinese => {
      slug = slug.replace(new RegExp(chinese, 'g'), chineseToPinyin[chinese]);
    });
    
    // 处理剩余的中文字符：如果还有中文，则移除或用占位符替换
    slug = slug
      .replace(/[\u4e00-\u9fa5]/g, '') // 移除剩余中文字符
      .replace(/[^a-z0-9]/g, '-')      // 非字母数字替换为连字符
      .replace(/--+/g, '-')            // 多个连字符合并为一个
      .replace(/^-|-$/g, '');          // 去除首尾连字符
    
    // 如果生成的slug为空，使用时间戳
    if (!slug) {
      slug = 'tag-' + Date.now().toString().slice(-6);
    }
    
    form.slug = slug;
  }
};

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return;
  
  try {
    await formRef.value.validate();
    
    submitting.value = true;
    
    const data = {
      name: form.name.trim(),
      slug: form.slug.trim() || undefined
    };
    
    let response;
    if (dialogMode.value === 'create') {
      response = await api.post('/taxonomy/tags/', data);
    } else {
      response = await api.patch(`/taxonomy/tags/${editingId.value}`, data);
    }
    
    if (response.data.code === 0) {
      ElMessage.success(
        dialogMode.value === 'create' ? '标签创建成功' : '标签更新成功'
      );
      dialogVisible.value = false;
      await loadData();
    } else {
      ElMessage.error(response.data.message || '操作失败');
    }
  } catch (error) {
    if (error !== 'validation failed') {
      console.error('提交失败:', error);
      
      // 根据错误类型提供更详细的错误信息
      let errorMessage = '操作失败';
      if (error.response?.status === 401) {
        errorMessage = '认证失败，请重新登录';
      } else if (error.response?.status === 403) {
        errorMessage = '权限不足，需要编辑者或管理员权限';
      } else if (error.response?.status === 409) {
        errorMessage = '标签名称或Slug已存在，请使用其他名称';
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      }
      
      ElMessage({
        message: errorMessage,
        type: 'error',
        duration: 5000,
        showClose: true,
        customClass: 'modern-error-message'
      });
    }
  } finally {
    submitting.value = false;
  }
};

// 删除标签
const handleDelete = async (tag) => {
  if (tag.article_count > 0) {
    ElMessage.warning('该标签还在使用中，无法删除');
    return;
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除标签「${tag.name}」吗？此操作不可恢复！`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    );
    
    const response = await api.delete(`/taxonomy/tags/${tag.id}`);
    
    if (response.data.code === 0) {
      ElMessage.success('标签删除成功');
      await loadData();
    } else {
      ElMessage.error(response.data.message || '删除失败');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error);
      ElMessage.error('删除失败');
    }
  }
};

// 清理未使用的标签
const cleanUnusedTags = async () => {
  const unusedTags = tags.value.filter(tag => tag.article_count === 0);
  
  if (unusedTags.length === 0) {
    ElMessage.info('没有未使用的标签');
    return;
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${unusedTags.length} 个未使用的标签吗？此操作不可恢复！`,
      '清理确认',
      {
        type: 'warning',
        confirmButtonText: '确定清理',
        cancelButtonText: '取消'
      }
    );
    
    for (const tag of unusedTags) {
      await api.delete(`/taxonomy/tags/${tag.id}`);
    }
    
    ElMessage.success(`成功清理 ${unusedTags.length} 个未使用的标签`);
    await loadData();
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清理失败:', error);
      ElMessage.error('清理失败');
    }
  }
};

// 处理选择变化
const handleSelectionChange = (selection) => {
  selectedTags.value = selection;
};

// 处理搜索
const handleSearch = () => {
  // 搜索是响应式的，不需要额外处理
};

// 处理排序
const handleSort = () => {
  // 排序是响应式的，不需要额外处理
};

// 处理视图模式变化
const handleViewModeChange = () => {
  // 视图模式是响应式的，不需要额外处理
};

// 获取标签类型
const getTagType = (count) => {
  if (count === 0) return 'info';
  if (count >= 10) return 'danger';
  if (count >= 5) return 'warning';
  return 'success';
};

// 获取标签样式类
const getTagClass = (count) => {
  if (count === 0) return 'unused';
  if (count >= 10) return 'high-usage';
  if (count >= 5) return 'medium-usage';
  return 'low-usage';
};

// 获取使用百分比
const getUsagePercentage = (count) => {
  const maxCount = Math.max(...tags.value.map(t => t.article_count));
  return maxCount === 0 ? 0 : Math.round((count / maxCount) * 100);
};

// 获取进度条颜色
const getProgressColor = (count) => {
  if (count === 0) return '#e5e7eb';
  if (count >= 10) return '#ef4444';
  if (count >= 5) return '#f59e0b';
  return '#10b981';
};

// 获取进度条渐变
const getProgressGradient = (count) => {
  if (count === 0) return 'linear-gradient(135deg, #e5e7eb, #d1d5db)';
  if (count >= 10) return 'linear-gradient(135deg, #ef4444, #f87171)';
  if (count >= 5) return 'linear-gradient(135deg, #f59e0b, #fbbf24)';
  return 'linear-gradient(135deg, #8b5cf6, #a855f7)';
};

// 获取标签云样式
const getCloudTagStyle = (tag) => {
  const baseSize = 14;
  const maxSize = 32;
  const maxCount = Math.max(...tags.value.map(t => t.article_count));
  const size = maxCount === 0 ? baseSize : 
    baseSize + (tag.article_count / maxCount) * (maxSize - baseSize);
  
  return {
    fontSize: size + 'px',
    opacity: tag.article_count === 0 ? 0.5 : 1
  };
};

// 组件挂载时加载数据
onMounted(() => {
  loadData();
});
</script>

<style scoped>
/* ===== 现代化标签管理页面样式 ===== */
.tag-management {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
  background: 
    radial-gradient(circle at 20% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(168, 85, 247, 0.05) 0%, transparent 50%),
    radial-gradient(circle at 40% 40%, rgba(6, 182, 212, 0.05) 0%, transparent 50%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
}

/* 现代化页面头部 */
.modern-page-header {
  position: relative;
  background: 
    linear-gradient(135deg, rgba(139, 92, 246, 0.08), rgba(168, 85, 247, 0.05)),
    rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 2.5rem;
  margin-bottom: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.modern-page-header::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(168, 85, 247, 0.05));
  border-radius: 50%;
  filter: blur(40px);
  animation: float-decoration 8s ease-in-out infinite;
}

@keyframes float-decoration {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-30px) rotate(180deg); }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  position: relative;
  z-index: 2;
  margin-bottom: 1.5rem;
}

.title-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-icon {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 30px rgba(139, 92, 246, 0.3);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.title-icon::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.3) 50%, transparent 60%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.title-icon:hover::before {
  transform: rotate(45deg) translateX(100%);
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0 0 0.5rem 0;
  font-size: 2.25rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #8b5cf6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.page-description {
  margin: 0;
  color: #64748b;
  font-size: 1.125rem;
  font-weight: 400;
  line-height: 1.6;
}

/* 统计面板 */
.modern-stats {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  flex: 1;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #8b5cf6, #a855f7);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  border-color: rgba(139, 92, 246, 0.2);
}

.stat-card:hover::before {
  height: 4px;
  background: linear-gradient(90deg, #a855f7, #9333ea);
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.stat-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(168, 85, 247, 0.05));
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b5cf6;
  transition: all 0.3s ease;
}

.stat-card:hover .stat-icon {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(168, 85, 247, 0.1));
  transform: scale(1.1) rotate(5deg);
}

.stat-info {
  flex: 1;
}

.stat-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  display: block;
  font-size: 2rem;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
  transition: all 0.3s ease;
}

.stat-value.active {
  color: #8b5cf6;
}

.stat-value.unused {
  color: #f59e0b;
}

.stat-card:hover .stat-value {
  transform: scale(1.05);
}

/* 操作按钮组 */
.header-actions {
  display: flex;
  gap: 0.75rem;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 12px;
  border: none;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.action-btn.primary {
  background: linear-gradient(135deg, #8b5cf6, #a855f7);
  color: white;
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
}

.action-btn.primary:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4);
  background: linear-gradient(135deg, #a855f7, #9333ea);
}

.action-btn.danger {
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: white;
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
}

.action-btn.danger:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(239, 68, 68, 0.4);
  background: linear-gradient(135deg, #dc2626, #ef4444);
}

.action-btn.danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.8);
  color: #64748b;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.action-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.95);
  color: #1e293b;
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  border-color: rgba(139, 92, 246, 0.2);
}

.action-btn .is-loading {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 现代化筛选容器 */
.modern-filter-container {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  gap: 1rem;
  flex: 1;
  min-width: 0;
}

.modern-search-input,
.modern-select {
  flex: 1;
  min-width: 200px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  border: 1px solid rgba(139, 92, 246, 0.2);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  transition: all 0.3s ease;
}

.search-input :deep(.el-input__wrapper):hover {
  border-color: rgba(139, 92, 246, 0.4);
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.1);
}

.sort-select :deep(.el-select__wrapper) {
  border-radius: 12px;
  border: 1px solid rgba(139, 92, 246, 0.2);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
}

.modern-view-toggle {
  flex-shrink: 0;
}

.view-mode-selector :deep(.el-radio-button__inner) {
  border-radius: 8px;
  transition: all 0.3s ease;
}

.view-mode-selector :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #8b5cf6, #a855f7);
  border-color: #8b5cf6;
}

/* 现代化标签表格 */
.modern-tags-table {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  overflow: hidden;
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04);
  margin-bottom: 2rem;
}

.modern-table :deep(.el-table__header-wrapper) {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.05), rgba(168, 85, 247, 0.02));
  border-radius: 20px 20px 0 0;
}

.modern-table :deep(.el-table__header) {
  background: transparent;
}

.modern-table :deep(.el-table__header th) {
  background: transparent !important;
  border: none;
  color: #1e293b;
  font-weight: 700;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 1.5rem 1rem;
}

.modern-table :deep(.el-table__body tr) {
  transition: all 0.3s ease;
  border: none;
}

.modern-table :deep(.el-table__body tr:hover) {
  background: rgba(139, 92, 246, 0.02);
  transform: scale(1.005);
}

.modern-table :deep(.el-table__body td) {
  border: none;
  padding: 1.25rem 1rem;
  vertical-align: middle;
}

.modern-table :deep(.el-table::before) {
  display: none;
}

.modern-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

/* 现代化标签名称样式 */
.modern-tag-name {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tag-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.875rem;
  transition: all 0.3s ease;
  border: 1px solid;
}

.tag-badge.unused {
  background: linear-gradient(135deg, rgba(107, 114, 128, 0.1), rgba(156, 163, 175, 0.05));
  color: #6b7280;
  border-color: rgba(107, 114, 128, 0.2);
}

.tag-badge.low-usage {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(168, 85, 247, 0.05));
  color: #8b5cf6;
  border-color: rgba(139, 92, 246, 0.2);
}

.tag-badge.medium-usage {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(251, 191, 36, 0.05));
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.2);
}

.tag-badge.high-usage {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(248, 113, 113, 0.05));
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.2);
}

.tag-badge:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tag-text {
  font-weight: 600;
}

.usage-info {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.usage-count {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 500;
}

/* Slug 代码样式 */
.slug-code {
  background: rgba(139, 92, 246, 0.05);
  color: #8b5cf6;
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid rgba(139, 92, 246, 0.1);
  transition: all 0.3s ease;
}

.slug-code:hover {
  background: rgba(139, 92, 246, 0.1);
  transform: scale(1.05);
  border-color: rgba(139, 92, 246, 0.2);
}

/* 现代化使用情况显示 */
.modern-usage-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.usage-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
  width: 100%;
}

.progress-bar {
  width: 80px;
  height: 6px;
  background: rgba(229, 231, 235, 0.5);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { left: -100%; }
  100% { left: 100%; }
}

.usage-stats {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.125rem;
}

.usage-number {
  font-size: 0.875rem;
  font-weight: 700;
  color: #1e293b;
}

.usage-percentage {
  font-size: 0.75rem;
  font-weight: 500;
  color: #64748b;
}

/* 现代化表格操作按钮 */
.modern-action-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: center;
}

.table-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 8px;
  border: 1px solid;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
  min-width: fit-content;
}

.table-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.table-btn:hover::before {
  left: 100%;
}

.table-btn.edit {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(168, 85, 247, 0.05));
  color: #8b5cf6;
  border-color: rgba(139, 92, 246, 0.3);
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.15);
}

.table-btn.edit:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(168, 85, 247, 0.1));
  border-color: rgba(139, 92, 246, 0.4);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.25);
  transform: translateY(-2px) scale(1.02);
  color: #7c3aed;
}

.table-btn.delete {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(248, 113, 113, 0.05));
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}

.table-btn.delete:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(248, 113, 113, 0.1));
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.25);
  transform: translateY(-2px) scale(1.02);
  color: #dc2626;
}

.table-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none !important;
}

.table-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none !important;
}

.table-btn:disabled:hover {
  transform: none !important;
}

/* 现代化标签云 */
.modern-tag-cloud {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 2.5rem;
  min-height: 400px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
  margin-bottom: 2rem;
}

.cloud-container {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
  align-items: center;
}

.modern-cloud-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.75rem 1.25rem;
  background: linear-gradient(135deg, #8b5cf6, #a855f7);
  color: white;
  border-radius: 25px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 600;
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.2);
  position: relative;
  overflow: hidden;
}

.modern-cloud-tag::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.2) 50%, transparent 60%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.modern-cloud-tag:hover::before {
  transform: rotate(45deg) translateX(100%);
}

.modern-cloud-tag:hover {
  transform: translateY(-4px) scale(1.1);
  box-shadow: 0 8px 30px rgba(139, 92, 246, 0.3);
}

.modern-cloud-tag.unused {
  background: linear-gradient(135deg, #e5e7eb, #d1d5db);
  color: #6b7280;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.modern-cloud-tag.unused:hover {
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.tag-text {
  line-height: 1;
  font-weight: 600;
}

.tag-count {
  font-size: 0.875em;
  opacity: 0.9;
  font-weight: 500;
}

/* 现代化空状态样式 */
.modern-empty-state {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 4rem 3rem;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
  margin: 2rem 0;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
}

.empty-icon {
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(168, 85, 247, 0.05));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b5cf6;
  margin-bottom: 1rem;
  position: relative;
  overflow: hidden;
}

.empty-icon::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 40%, rgba(139, 92, 246, 0.1) 50%, transparent 60%);
  transform: rotate(45deg);
  animation: spin-slow 8s linear infinite;
}

@keyframes spin-slow {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.empty-description {
  font-size: 1rem;
  color: #64748b;
  line-height: 1.6;
  max-width: 400px;
  margin: 0;
}

.empty-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #8b5cf6, #a855f7);
  color: white;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
}

.empty-action-btn:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4);
  background: linear-gradient(135deg, #a855f7, #9333ea);
}

/* 现代化对话框样式 */
.modern-dialog :deep(.el-dialog) {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 0;
  border: none;
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 1.5rem;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 1.5rem 0;
  border-bottom: 1px solid rgba(139, 92, 246, 0.1);
  margin-bottom: 1.5rem;
}

.dialog-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
}

.dialog-icon {
  color: #8b5cf6;
}

.dialog-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog-close:hover {
  background: rgba(139, 92, 246, 0.2);
  transform: scale(1.1);
}

.modern-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(139, 92, 246, 0.1);
  margin-top: 1.5rem;
}

.dialog-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 8px;
  border: 1px solid;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.dialog-btn.primary {
  background: linear-gradient(135deg, #8b5cf6, #a855f7);
  color: white;
  border-color: #8b5cf6;
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
}

.dialog-btn.primary:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4);
  background: linear-gradient(135deg, #a855f7, #9333ea);
}

.dialog-btn.secondary {
  background: rgba(255, 255, 255, 0.8);
  color: #64748b;
  border-color: rgba(139, 92, 246, 0.2);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.dialog-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.95);
  color: #1e293b;
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  border-color: rgba(139, 92, 246, 0.3);
}

.dialog-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .modern-page-header {
    flex-direction: column;
    gap: 1.5rem;
    align-items: flex-start;
  }
  
  .title-container {
    width: 100%;
  }
  
  .modern-stats {
    width: 100%;
    justify-content: space-between;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
  
  .filter-row {
    flex-direction: column;
    gap: 1rem;
  }
  
  .filter-group {
    width: 100%;
  }
  
  .modern-view-toggle {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .tag-management {
    padding: 1rem;
  }
  
  .modern-page-header {
    padding: 1.5rem;
  }
  
  .title-container {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }
  
  .title-icon {
    width: 50px;
    height: 50px;
  }
  
  .page-title {
    font-size: 1.875rem;
  }
  
  .modern-stats {
    flex-direction: column;
    gap: 1rem;
  }
  
  .stat-card {
    width: 100%;
  }
  
  .header-actions {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .action-btn {
    width: 100%;
    justify-content: center;
  }
  
  .filter-group {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .modern-search-input,
  .modern-select {
    min-width: unset;
  }
  
  .modern-tags-table,
  .modern-tag-cloud {
    border-radius: 16px;
  }
  
  .modern-table :deep(.el-table__body-wrapper) {
    overflow-x: auto;
  }
  
  .modern-action-buttons {
    flex-direction: column;
    gap: 0.25rem;
  }
  
  .table-btn {
    width: 100%;
    justify-content: center;
    font-size: 0.75rem;
    padding: 0.5rem;
  }
  
  .cloud-container {
    gap: 0.5rem;
  }
  
  .modern-cloud-tag {
    padding: 0.5rem 1rem;
    font-size: 0.875rem !important;
  }
}

@media (max-width: 640px) {
  .modern-stats {
    gap: 0.75rem;
  }
  
  .stat-card {
    padding: 1rem;
  }
  
  .stat-icon {
    width: 40px;
    height: 40px;
  }
  
  .stat-value {
    font-size: 1.5rem;
  }
  
  .modern-tags-table,
  .modern-tag-cloud {
    border-radius: 12px;
  }
  
  .modern-filter-container {
    padding: 1rem;
    border-radius: 16px;
  }
}

/* ===== 现代化错误消息样式 ===== */
:deep(.modern-error-message) {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.95), rgba(220, 38, 38, 0.95));
  border: 1px solid rgba(239, 68, 68, 0.3);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  box-shadow: 
    0 8px 32px rgba(239, 68, 68, 0.2),
    0 1px 0 rgba(255, 255, 255, 0.2) inset;
  color: white;
  padding: 16px 20px;
  font-weight: 500;
}

:deep(.modern-error-message .el-message__content) {
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

:deep(.modern-error-message .el-message__closeBtn) {
  color: rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
}

:deep(.modern-error-message .el-message__closeBtn:hover) {
  color: white;
  transform: scale(1.1);
}

/* ===== Slug表单增强样式 ===== */
.slug-help-icon {
  color: #94a3b8;
  transition: all 0.3s ease;
  cursor: help;
}

.slug-help-icon:hover {
  color: #3b82f6;
  transform: scale(1.1);
}

.slug-preview {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(59, 130, 246, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 8px;
  font-size: 0.875rem;
}

.preview-label {
  color: #64748b;
  font-weight: 500;
  margin-right: 8px;
}

.preview-url {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 0.8rem;
}
</style>