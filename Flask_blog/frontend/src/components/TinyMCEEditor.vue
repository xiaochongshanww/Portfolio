<template>
  <div class="tinymce-editor-container">
    <!-- 编辑器提示 -->
    <div class="editor-header">
      <div class="header-info">
        <el-icon class="info-icon"><InfoFilled /></el-icon>
        <span>支持从Typora、Word等工具直接复制粘贴富文本内容</span>
      </div>
      <div class="header-actions">
        <el-button size="small" @click="handleClear" type="danger" plain>
          <el-icon><Delete /></el-icon>
          清空内容
        </el-button>
        <el-button size="small" @click="handleWordCount" type="info" plain>
          <el-icon><DocumentCopy /></el-icon>
          字数统计
        </el-button>
      </div>
    </div>

    <!-- TinyMCE编辑器 -->
    <Editor
      v-model="content"
      :init="editorConfig"
      @input="handleInput"
      @change="handleChange"
    />

    <!-- 字数统计对话框 -->
    <el-dialog v-model="wordCountVisible" title="字数统计" width="400px">
      <div class="word-count-stats">
        <div class="stat-item">
          <span class="stat-label">字符数：</span>
          <span class="stat-value">{{ wordStats.characters }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">单词数：</span>
          <span class="stat-value">{{ wordStats.words }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">段落数：</span>
          <span class="stat-value">{{ wordStats.paragraphs }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import Editor from '@tinymce/tinymce-vue';
import { InfoFilled, Delete, DocumentCopy } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import TurndownService from 'turndown';

// 加载TinyMCE
onMounted(() => {
  // 如果TinyMCE还未加载，从免费CDN加载
  if (typeof window.tinymce === 'undefined') {
    const script = document.createElement('script');
    // 使用cdnjs免费CDN，无需API KEY
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/tinymce/7.4.1/tinymce.min.js';
    script.integrity = 'sha512-6B6f4SN7X/wZ4zdGBGJx/1c7/3RwAYY6uV2EjdYT8Vwl5ql8aWrwzEzKwLKFOJYX+YEfSQKrPU3fgmEjBKCZXQ==';
    script.crossOrigin = 'anonymous';
    script.referrerPolicy = 'no-referrer';
    document.head.appendChild(script);
    console.log('正在从cdnjs加载TinyMCE，无需API KEY');
  }
});

// Props
interface Props {
  modelValue: string;
  height?: number;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  height: 500
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

// 响应式数据
const content = ref('');
const wordCountVisible = ref(false);
const wordStats = ref({
  characters: 0,
  words: 0,
  paragraphs: 0
});

// 使用CDN版本，无需API KEY

// Turndown服务用于HTML转Markdown
const turndownService = new TurndownService({
  headingStyle: 'atx',
  bulletListMarker: '-',
  codeBlockStyle: 'fenced',
  fence: '```'
});

// 配置代码块转换规则
turndownService.addRule('codeBlock', {
  filter: ['pre'],
  replacement: function (content, node) {
    const language = node.getAttribute('class')?.replace('language-', '') || '';
    return '\n```' + language + '\n' + content + '\n```\n';
  }
});

// TinyMCE编辑器配置
const editorConfig = computed(() => ({
  height: props.height,
  menubar: false,
  branding: false,
  language: 'zh_CN',
  plugins: [
    'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
    'anchor', 'searchreplace', 'visualblocks', 'codesample', 'fullscreen',
    'insertdatetime', 'media', 'table', 'help', 'wordcount', 'quickbars'
  ],
  toolbar: [
    'undo redo | bold italic underline strikethrough | fontsize forecolor backcolor',
    'alignleft aligncenter alignright alignjustify | bullist numlist outdent indent',
    'removeformat | link image media table codesample | preview fullscreen help'
  ].join(' | '),
  quickbars_selection_toolbar: 'bold italic | quicklink h2 h3 blockquote quickimage quicktable',
  quickbars_insert_toolbar: 'quickimage quicktable',
  contextmenu: 'link image table',
  
  // 内容样式
  content_style: `
    body {
      font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
      font-size: 16px;
      line-height: 1.6;
      color: #333;
      max-width: 100%;
      margin: 0;
      padding: 20px;
    }
    h1, h2, h3, h4, h5, h6 {
      font-weight: 600;
      margin: 1.5em 0 0.5em 0;
      color: #1f2937;
    }
    p {
      margin: 1em 0;
    }
    blockquote {
      border-left: 4px solid #e5e7eb;
      padding-left: 16px;
      margin: 1em 0;
      color: #6b7280;
      font-style: italic;
    }
    pre {
      background: #f8f9fa;
      border: 1px solid #e5e7eb;
      border-radius: 6px;
      padding: 16px;
      overflow-x: auto;
      font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
    }
    code {
      background: #f1f5f9;
      padding: 2px 4px;
      border-radius: 3px;
      font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
      font-size: 0.9em;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 1em 0;
    }
    table td, table th {
      border: 1px solid #e5e7eb;
      padding: 8px 12px;
      text-align: left;
    }
    table th {
      background: #f9fafb;
      font-weight: 600;
    }
  `,
  
  // 高级配置
  paste_data_images: true,
  paste_as_text: false,
  paste_webkit_styles: 'font-weight font-style color text-decoration',
  paste_retain_style_properties: 'color font-size font-family font-weight font-style text-decoration',
  
  // 图片上传配置
  images_upload_handler: (blobInfo: any, progress: any) => {
    return new Promise((resolve, reject) => {
      // 这里可以实现图片上传到服务器的逻辑
      // 临时方案：转换为base64
      const reader = new FileReader();
      reader.onload = () => {
        resolve(reader.result as string);
      };
      reader.onerror = () => {
        reject('图片上传失败');
      };
      reader.readAsDataURL(blobInfo.blob());
    });
  },
  
  // 代码示例语言
  codesample_languages: [
    { text: 'HTML/XML', value: 'markup' },
    { text: 'JavaScript', value: 'javascript' },
    { text: 'CSS', value: 'css' },
    { text: 'Python', value: 'python' },
    { text: 'Java', value: 'java' },
    { text: 'C++', value: 'cpp' },
    { text: 'C#', value: 'csharp' },
    { text: 'PHP', value: 'php' },
    { text: 'Ruby', value: 'ruby' },
    { text: 'Go', value: 'go' },
    { text: 'Rust', value: 'rust' },
    { text: 'TypeScript', value: 'typescript' },
    { text: 'Bash', value: 'bash' },
    { text: 'SQL', value: 'sql' },
    { text: 'JSON', value: 'json' },
    { text: 'Markdown', value: 'markdown' }
  ],
  
  // 设置功能
  setup: (editor: any) => {
    editor.on('init', () => {
      console.log('TinyMCE编辑器初始化完成');
    });
  }
}));

// 处理输入变化
function handleInput() {
  updateModelValue();
}

// 处理内容变化
function handleChange() {
  updateModelValue();
}

// 更新模型值
function updateModelValue() {
  // 将HTML转换为Markdown
  const markdown = turndownService.turndown(content.value || '');
  emit('update:modelValue', markdown);
}

// 清空内容
async function handleClear() {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有内容吗？此操作不可恢复。',
      '确认清空',
      {
        type: 'warning',
        confirmButtonText: '确认清空',
        cancelButtonText: '取消'
      }
    );
    
    content.value = '';
    updateModelValue();
    ElMessage.success('内容已清空');
  } catch (error) {
    // 用户取消操作
  }
}

// 字数统计
function handleWordCount() {
  const text = content.value.replace(/<[^>]*>/g, ''); // 移除HTML标签
  const characters = text.length;
  const words = text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
  const paragraphs = content.value.split(/<\/p>/i).length - 1;
  
  wordStats.value = {
    characters,
    words,
    paragraphs
  };
  
  wordCountVisible.value = true;
}

// 监听props变化
watch(() => props.modelValue, (newValue) => {
  if (newValue && newValue !== turndownService.turndown(content.value || '')) {
    // 如果是Markdown，转换为HTML
    if (!newValue.includes('<')) {
      // 简单的Markdown到HTML转换
      content.value = newValue
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/^(?!<h|<p)(.+)/gm, '<p>$1</p>')
        .replace(/<p><\/p>/g, '');
    } else {
      content.value = newValue;
    }
  }
}, { immediate: true });

// 暴露方法给父组件
defineExpose({
  syncContent() {
    updateModelValue();
    return turndownService.turndown(content.value || '');
  },
  getContent() {
    return turndownService.turndown(content.value || '');
  },
  setContent(newContent: string) {
    content.value = newContent;
    updateModelValue();
  },
  getHTML() {
    return content.value;
  }
});
</script>

<style scoped>
.tinymce-editor-container {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
}

.info-icon {
  color: #3b82f6;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.word-count-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #6b7280;
}

.stat-value {
  font-weight: 600;
  color: #1f2937;
}

/* TinyMCE样式覆盖 */
:deep(.tox) {
  border: none;
}

:deep(.tox-tinymce) {
  border-radius: 0 0 8px 8px;
}

:deep(.tox .tox-editor-header) {
  border: none;
  border-bottom: 1px solid #e5e7eb;
}

:deep(.tox .tox-toolbar-overlord) {
  background: #fefefe;
}

:deep(.tox .tox-edit-area) {
  border: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .editor-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .header-info {
    justify-content: center;
    text-align: center;
  }
  
  .header-actions {
    justify-content: center;
  }
}
</style>