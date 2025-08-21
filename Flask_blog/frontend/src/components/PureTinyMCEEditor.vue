<template>
  <div class="pure-tinymce-editor">
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

    <!-- 原生textarea编辑器容器 -->
    <div class="editor-container">
      <textarea 
        ref="editorRef" 
        v-model="content" 
        :id="editorId"
        class="tinymce-textarea"
      ></textarea>
    </div>

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
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { InfoFilled, Delete, DocumentCopy } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import TurndownService from 'turndown';

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
const editorRef = ref<HTMLTextAreaElement>();
const content = ref('');
const editorId = ref(`tinymce-${Date.now()}`);
const wordCountVisible = ref(false);
const isEditorReady = ref(false);
const wordStats = ref({
  characters: 0,
  words: 0,
  paragraphs: 0
});

let tinymceEditor: any = null;

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

// 加载TinyMCE并初始化
async function loadTinyMCE() {
  return new Promise((resolve, reject) => {
    // 如果已经加载过，直接返回
    if (window.tinymce) {
      console.log('TinyMCE已存在，直接使用');
      resolve(window.tinymce);
      return;
    }

    console.log('开始加载TinyMCE...');
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/tinymce/7.4.1/tinymce.min.js';
    script.integrity = 'sha512-6B6f4SN7X/wZ4zdGBGJx/1c7/3RwAYY6uV2EjdYT8Vwl5ql8aWrwzEzKwLKFOJYX+YEfSQKrPU3fgmEjBKCZXQ==';
    script.crossOrigin = 'anonymous';
    script.referrerPolicy = 'no-referrer';
    
    script.onload = () => {
      console.log('TinyMCE脚本加载成功，tinymce对象:', window.tinymce);
      // 等待一下确保完全初始化
      setTimeout(() => {
        resolve(window.tinymce);
      }, 100);
    };
    
    script.onerror = (error) => {
      console.error('TinyMCE脚本加载失败:', error);
      reject(new Error('TinyMCE加载失败'));
    };
    
    document.head.appendChild(script);
  });
}

// 初始化编辑器
async function initEditor() {
  try {
    await loadTinyMCE();
    await nextTick();

    if (!window.tinymce || !editorRef.value) {
      throw new Error('TinyMCE未加载或编辑器元素不存在');
    }

    // TinyMCE配置
    const config = {
      selector: `#${editorId.value}`, // 使用selector而非target
      height: props.height,
      menubar: false,
      branding: false,
      plugins: [
        'advlist', 'autolink', 'lists', 'link', 'image', 'charmap',
        'searchreplace', 'visualblocks', 'codesample', 'fullscreen',
        'insertdatetime', 'table', 'help', 'wordcount', 'paste'
      ],
      toolbar: [
        'undo redo | bold italic underline strikethrough',
        'formatselect | fontsize forecolor backcolor',
        'alignleft aligncenter alignright alignjustify',
        'bullist numlist outdent indent | removeformat',
        'link image table codesample | fullscreen help'
      ].join(' | '),
      
      // 确保工具栏换行
      toolbar_mode: 'sliding',
      
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
        p { margin: 1em 0; }
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
      `,
      
      // 粘贴配置 - 关键！
      paste_data_images: true,
      paste_as_text: false,
      paste_retain_style_properties: 'font-weight font-style color text-decoration text-align',
      paste_webkit_styles: 'font-weight font-style color text-decoration text-align',
      paste_merge_formats: true,
      paste_auto_cleanup_on_paste: false,
      
      // 代码示例语言
      codesample_languages: [
        { text: 'HTML/XML', value: 'markup' },
        { text: 'JavaScript', value: 'javascript' },
        { text: 'CSS', value: 'css' },
        { text: 'Python', value: 'python' },
        { text: 'Java', value: 'java' },
        { text: 'TypeScript', value: 'typescript' },
        { text: 'Bash', value: 'bash' }
      ],
      
      // 事件处理
      setup: (editor: any) => {
        editor.on('init', () => {
          console.log('TinyMCE编辑器初始化完成');
          isEditorReady.value = true;
          
          // 设置初始内容
          if (props.modelValue) {
            const htmlContent = props.modelValue.includes('<') ? 
              props.modelValue : 
              markdownToHtml(props.modelValue);
            editor.setContent(htmlContent);
          }
        });
        
        editor.on('change input', () => {
          updateModelValue();
        });
      }
    };

    // 初始化编辑器
    const editors = await window.tinymce.init(config);
    if (editors && editors.length > 0) {
      tinymceEditor = editors[0];
    } else {
      // 获取编辑器实例
      tinymceEditor = window.tinymce.get(editorId.value);
    }
    
    console.log('TinyMCE编辑器创建成功', tinymceEditor);
    
  } catch (error) {
    console.error('初始化编辑器失败:', error);
    ElMessage.error('编辑器加载失败，请刷新页面重试');
  }
}

// 简单的Markdown转HTML
function markdownToHtml(markdown: string): string {
  return markdown
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[h|p])(.+)/gm, '<p>$1</p>')
    .replace(/<p><\/p>/g, '');
}

// 更新模型值
function updateModelValue() {
  if (!tinymceEditor || !isEditorReady.value) return;
  
  try {
    const htmlContent = tinymceEditor.getContent();
    console.log('获取到HTML内容:', htmlContent.substring(0, 100) + '...');
    const markdown = turndownService.turndown(htmlContent);
    console.log('转换后的Markdown:', markdown.substring(0, 100) + '...');
    emit('update:modelValue', markdown);
  } catch (error) {
    console.error('更新内容失败:', error);
  }
}

// 清空内容
async function handleClear() {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有内容吗？此操作不可恢复。',
      '确认清空',
      { type: 'warning' }
    );
    
    if (tinymceEditor && isEditorReady.value) {
      tinymceEditor.setContent('');
      updateModelValue();
    }
    ElMessage.success('内容已清空');
  } catch (error) {
    // 用户取消操作
  }
}

// 字数统计
function handleWordCount() {
  if (!tinymceEditor || !isEditorReady.value) return;
  
  const content = tinymceEditor.getContent();
  const text = content.replace(/<[^>]*>/g, '');
  
  wordStats.value = {
    characters: text.length,
    words: text.trim() === '' ? 0 : text.trim().split(/\s+/).length,
    paragraphs: content.split(/<\/p>/i).length - 1
  };
  
  wordCountVisible.value = true;
}

// 监听props变化
watch(() => props.modelValue, (newValue) => {
  if (tinymceEditor && isEditorReady.value && newValue) {
    const currentMarkdown = turndownService.turndown(tinymceEditor.getContent() || '');
    if (newValue !== currentMarkdown) {
      const htmlContent = newValue.includes('<') ? newValue : markdownToHtml(newValue);
      tinymceEditor.setContent(htmlContent);
    }
  }
});

// 生命周期
onMounted(() => {
  initEditor();
});

onBeforeUnmount(() => {
  if (tinymceEditor) {
    try {
      tinymceEditor.destroy();
    } catch (error) {
      console.error('销毁编辑器失败:', error);
    }
  }
});

// 暴露方法
defineExpose({
  syncContent() {
    updateModelValue();
    if (tinymceEditor && isEditorReady.value) {
      return turndownService.turndown(tinymceEditor.getContent() || '');
    }
    return '';
  },
  getContent() {
    if (tinymceEditor && isEditorReady.value) {
      return turndownService.turndown(tinymceEditor.getContent() || '');
    }
    return '';
  },
  setContent(newContent: string) {
    if (tinymceEditor && isEditorReady.value) {
      const htmlContent = newContent.includes('<') ? newContent : markdownToHtml(newContent);
      tinymceEditor.setContent(htmlContent);
      updateModelValue();
    }
  }
});
</script>

<style scoped>
.pure-tinymce-editor {
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

.editor-container {
  position: relative;
}

.tinymce-textarea {
  width: 100%;
  min-height: 500px;
  border: none;
  outline: none;
  resize: none;
  padding: 16px;
  font-family: inherit;
  font-size: 16px;
  line-height: 1.6;
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