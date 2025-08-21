<template>
  <div class="simple-tinymce">
    <!-- 编辑器状态提示 -->
    <div v-if="!isEditorReady" class="loading-state">
      <el-alert 
        title="编辑器加载中..." 
        type="info" 
        :closable="false"
        show-icon
      >
        <p>正在从CDN加载TinyMCE编辑器，请稍候...</p>
      </el-alert>
    </div>

    <!-- 编辑器容器 -->
    <div v-show="isEditorReady" class="editor-wrapper">
      <div class="editor-info">
        <el-icon><InfoFilled /></el-icon>
        <span>支持从Typora、Word等工具直接粘贴富文本内容</span>
      </div>
      <div :id="editorId" class="tinymce-container"></div>
    </div>

    <!-- 错误状态 -->
    <div v-if="hasError" class="error-state">
      <el-alert 
        title="编辑器加载失败" 
        type="error" 
        :closable="false"
        show-icon
      >
        <p>无法加载TinyMCE编辑器，请检查网络连接或刷新页面重试。</p>
        <el-button @click="retryInit" type="primary" size="small">重试</el-button>
      </el-alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { InfoFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import TurndownService from 'turndown';

// Props
interface Props {
  modelValue: string;
  height?: number;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  height: 400
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

// 响应式数据
const editorId = `tinymce-${Date.now()}`;
const isEditorReady = ref(false);
const hasError = ref(false);
let editor: any = null;

// Turndown服务
const turndownService = new TurndownService({
  headingStyle: 'atx',
  bulletListMarker: '-',
  codeBlockStyle: 'fenced'
});

// 加载TinyMCE
async function loadTinyMCE(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.tinymce) {
      resolve();
      return;
    }

    console.log('加载TinyMCE from CDN...');
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/tinymce@7/tinymce.min.js';
    script.onload = () => {
      console.log('TinyMCE加载成功');
      resolve();
    };
    script.onerror = () => {
      console.error('TinyMCE加载失败');
      reject(new Error('TinyMCE加载失败'));
    };
    
    document.head.appendChild(script);
  });
}

// 初始化编辑器
async function initEditor() {
  try {
    hasError.value = false;
    
    // 加载TinyMCE
    await loadTinyMCE();
    await nextTick();

    console.log('开始初始化TinyMCE编辑器...');
    
    // 确保容器存在
    const container = document.getElementById(editorId);
    if (!container) {
      throw new Error('编辑器容器不存在');
    }

    // 初始化配置
    await window.tinymce.init({
      selector: `#${editorId}`,
      height: props.height,
      menubar: false,
      branding: false,
      
      // 基础插件
      plugins: [
        'lists', 'link', 'image', 'charmap', 'preview', 'anchor', 
        'searchreplace', 'visualblocks', 'code', 'fullscreen',
        'insertdatetime', 'table', 'help', 'wordcount', 'paste'
      ],
      
      // 工具栏
      toolbar: 'undo redo | formatselect | bold italic underline strikethrough | ' +
               'alignleft aligncenter alignright alignjustify | ' +
               'bullist numlist outdent indent | ' +
               'removeformat | link image table | help',
      
      // 内容样式
      content_style: `
        body { 
          font-family: Helvetica, Arial, sans-serif; 
          font-size: 14px;
          line-height: 1.6;
          color: #333;
        }
        h1, h2, h3, h4, h5, h6 {
          font-weight: 600;
          margin: 1em 0 0.5em 0;
        }
      `,
      
      // 粘贴配置
      paste_data_images: true,
      paste_as_text: false,
      
      // 初始化完成回调
      init_instance_callback: (ed: any) => {
        console.log('TinyMCE编辑器初始化完成');
        editor = ed;
        isEditorReady.value = true;
        
        // 设置初始内容
        if (props.modelValue) {
          const htmlContent = isHTML(props.modelValue) ? 
            props.modelValue : 
            simpleMarkdownToHtml(props.modelValue);
          ed.setContent(htmlContent);
        }
        
        // 监听内容变化
        ed.on('input change', () => {
          updateModelValue();
        });
        
        ElMessage.success('编辑器加载完成！');
      }
    });
    
  } catch (error) {
    console.error('初始化编辑器失败:', error);
    hasError.value = true;
    ElMessage.error('编辑器初始化失败');
  }
}

// 判断是否为HTML
function isHTML(str: string): boolean {
  return /<\/?[a-z][\s\S]*>/i.test(str);
}

// 简单的Markdown转HTML
function simpleMarkdownToHtml(markdown: string): string {
  return markdown
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^(.+)/gm, '<p>$1</p>')
    .replace(/<p><\/p>/g, '');
}

// 更新模型值
function updateModelValue() {
  if (!editor || !isEditorReady.value) return;
  
  try {
    const htmlContent = editor.getContent();
    const markdown = turndownService.turndown(htmlContent);
    emit('update:modelValue', markdown);
  } catch (error) {
    console.error('更新内容失败:', error);
  }
}

// 重试初始化
async function retryInit() {
  console.log('重试初始化编辑器...');
  hasError.value = false;
  isEditorReady.value = false;
  
  // 销毁现有编辑器
  if (editor) {
    try {
      editor.destroy();
    } catch (e) {
      console.warn('销毁编辑器时出错:', e);
    }
    editor = null;
  }
  
  // 重新初始化
  await nextTick();
  initEditor();
}

// 监听props变化
watch(() => props.modelValue, (newValue) => {
  if (!editor || !isEditorReady.value || !newValue) return;
  
  const currentMarkdown = turndownService.turndown(editor.getContent());
  if (newValue !== currentMarkdown) {
    const htmlContent = isHTML(newValue) ? newValue : simpleMarkdownToHtml(newValue);
    editor.setContent(htmlContent);
  }
});

// 生命周期
onMounted(() => {
  console.log('组件挂载，开始初始化编辑器...');
  initEditor();
});

onBeforeUnmount(() => {
  if (editor) {
    try {
      editor.destroy();
    } catch (error) {
      console.error('销毁编辑器失败:', error);
    }
  }
});

// 暴露方法
defineExpose({
  syncContent() {
    updateModelValue();
    return editor ? turndownService.turndown(editor.getContent()) : '';
  },
  getContent() {
    return editor ? turndownService.turndown(editor.getContent()) : '';
  },
  setContent(content: string) {
    if (editor && isEditorReady.value) {
      const html = isHTML(content) ? content : simpleMarkdownToHtml(content);
      editor.setContent(html);
      updateModelValue();
    }
  }
});
</script>

<style scoped>
.simple-tinymce {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  min-height: 200px;
}

.loading-state,
.error-state {
  padding: 20px;
}

.editor-wrapper {
  position: relative;
}

.editor-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
  color: #6b7280;
}

.editor-info .el-icon {
  color: #3b82f6;
}

.tinymce-container {
  min-height: 400px;
}

/* 确保TinyMCE正确显示 */
:deep(.tox) {
  border: none !important;
  border-radius: 0 !important;
}

:deep(.tox-tinymce) {
  border: none !important;
  border-radius: 0 0 8px 8px !important;
}

:deep(.tox .tox-editor-header) {
  border: none !important;
  border-bottom: 1px solid #e5e7eb !important;
}
</style>