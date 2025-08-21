<template>
  <div class="simple-html-editor">
    <!-- 工具提示 -->
    <div class="editor-tips">
      <el-alert 
        title="使用提示" 
        type="info" 
        :closable="false"
        show-icon
      >
        <p>支持直接粘贴从 Typora、Word 或其他编辑器导出的 HTML 内容</p>
        <p>也可以直接输入 Markdown 或 HTML 代码</p>
      </el-alert>
    </div>

    <!-- 编辑器模式切换 -->
    <div class="editor-toolbar">
      <el-radio-group v-model="editMode" @change="handleModeChange">
        <el-radio-button value="visual">可视化编辑</el-radio-button>
        <el-radio-button value="html">HTML源码</el-radio-button>
        <el-radio-button value="markdown">Markdown</el-radio-button>
      </el-radio-group>
      
      <div class="toolbar-actions">
        <el-button 
          size="small" 
          @click="handlePasteHTML"
          :disabled="editMode === 'visual'"
        >
          <el-icon><DocumentCopy /></el-icon>
          粘贴HTML
        </el-button>
        <el-button 
          size="small" 
          @click="handleClearContent"
        >
          <el-icon><Delete /></el-icon>
          清空内容
        </el-button>
        <el-button 
          size="small" 
          @click="handlePreview"
          v-if="editMode !== 'visual'"
        >
          <el-icon><View /></el-icon>
          预览
        </el-button>
      </div>
    </div>

    <!-- 可视化编辑器 -->
    <div v-if="editMode === 'visual'" class="visual-editor">
      <editor-content :editor="editor" />
    </div>

    <!-- HTML源码编辑器 -->
    <div v-else-if="editMode === 'html'" class="code-editor">
      <el-input
        v-model="htmlContent"
        type="textarea"
        :rows="20"
        placeholder="请输入或粘贴HTML代码..."
        @input="handleHTMLChange"
      />
    </div>

    <!-- Markdown编辑器 -->
    <div v-else-if="editMode === 'markdown'" class="code-editor">
      <el-input
        v-model="markdownContent"
        type="textarea"
        :rows="20"
        placeholder="请输入Markdown代码..."
        @input="handleMarkdownChange"
      />
    </div>

    <!-- 预览对话框 -->
    <el-dialog 
      v-model="previewVisible" 
      title="内容预览" 
      width="80%"
      top="5vh"
    >
      <div class="preview-content" v-html="previewHTML"></div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { Editor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import MarkdownIt from 'markdown-it';
import TurndownService from 'turndown';
import { DocumentCopy, Delete, View } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

// Props
interface Props {
  modelValue: string;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: ''
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

// 响应式数据
const editMode = ref<'visual' | 'html' | 'markdown'>('visual');
const htmlContent = ref('');
const markdownContent = ref('');
const previewVisible = ref(false);
const previewHTML = ref('');
const editor = ref<Editor | null>(null);

// Markdown解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
});

// HTML转Markdown服务
const turndownService = new TurndownService({
  headingStyle: 'atx',
  bulletListMarker: '-',
  codeBlockStyle: 'fenced'
});

// 创建简单的TipTap编辑器
function createEditor() {
  editor.value = new Editor({
    extensions: [
      StarterKit.configure({
        // 使用默认配置，保持简单
      }),
    ],
    content: props.modelValue ? (isHTML(props.modelValue) ? props.modelValue : md.render(props.modelValue)) : '',
    onUpdate: ({ editor }) => {
      syncContent();
    },
  });
}

// 判断内容是否为HTML
function isHTML(str: string): boolean {
  return /<\/?[a-z][\s\S]*>/i.test(str);
}

// 同步内容到父组件
function syncContent() {
  if (!editor.value) return;

  let content = '';
  
  switch (editMode.value) {
    case 'visual':
      // 从可视化编辑器获取HTML，然后转换为Markdown
      content = turndownService.turndown(editor.value.getHTML());
      break;
    case 'html':
      // 从HTML转换为Markdown
      content = turndownService.turndown(htmlContent.value);
      break;
    case 'markdown':
      content = markdownContent.value;
      break;
  }
  
  emit('update:modelValue', content);
}

// 处理模式切换
function handleModeChange(newMode: string) {
  if (!editor.value) return;

  const currentHTML = editor.value.getHTML();
  
  switch (newMode) {
    case 'html':
      htmlContent.value = currentHTML;
      break;
    case 'markdown':
      markdownContent.value = turndownService.turndown(currentHTML);
      break;
    case 'visual':
      // 从其他模式切换回可视化时更新编辑器内容
      if (editMode.value === 'html') {
        editor.value.commands.setContent(htmlContent.value);
      } else if (editMode.value === 'markdown') {
        editor.value.commands.setContent(md.render(markdownContent.value));
      }
      break;
  }
  
  syncContent();
}

// 处理HTML变化
function handleHTMLChange() {
  syncContent();
}

// 处理Markdown变化
function handleMarkdownChange() {
  syncContent();
}

// 粘贴HTML功能
async function handlePasteHTML() {
  try {
    const clipboardText = await navigator.clipboard.readText();
    
    if (editMode.value === 'html') {
      htmlContent.value = clipboardText;
      handleHTMLChange();
    } else if (editMode.value === 'markdown') {
      // 将剪贴板HTML转换为Markdown
      const markdownText = turndownService.turndown(clipboardText);
      markdownContent.value = markdownText;
      handleMarkdownChange();
    }
    
    ElMessage.success('HTML内容已粘贴');
  } catch (error) {
    ElMessage.warning('无法读取剪贴板内容，请手动粘贴');
  }
}

// 清空内容
function handleClearContent() {
  switch (editMode.value) {
    case 'visual':
      editor.value?.commands.setContent('');
      break;
    case 'html':
      htmlContent.value = '';
      handleHTMLChange();
      break;
    case 'markdown':
      markdownContent.value = '';
      handleMarkdownChange();
      break;
  }
  ElMessage.success('内容已清空');
}

// 预览功能
function handlePreview() {
  if (editMode.value === 'html') {
    previewHTML.value = htmlContent.value;
  } else if (editMode.value === 'markdown') {
    previewHTML.value = md.render(markdownContent.value);
  }
  previewVisible.value = true;
}

// 监听props变化
watch(() => props.modelValue, (newValue) => {
  if (!newValue) return;
  
  if (editMode.value === 'visual' && editor.value) {
    const content = isHTML(newValue) ? newValue : md.render(newValue);
    if (content !== editor.value.getHTML()) {
      editor.value.commands.setContent(content);
    }
  } else if (editMode.value === 'html') {
    const content = isHTML(newValue) ? newValue : md.render(newValue);
    if (content !== htmlContent.value) {
      htmlContent.value = content;
    }
  } else if (editMode.value === 'markdown') {
    if (newValue !== markdownContent.value) {
      markdownContent.value = newValue;
    }
  }
});

// 生命周期
onMounted(() => {
  createEditor();
  
  // 初始化内容
  if (props.modelValue) {
    if (isHTML(props.modelValue)) {
      htmlContent.value = props.modelValue;
      markdownContent.value = turndownService.turndown(props.modelValue);
    } else {
      markdownContent.value = props.modelValue;
      htmlContent.value = md.render(props.modelValue);
    }
  }
});

onBeforeUnmount(() => {
  if (editor.value) {
    editor.value.destroy();
  }
});

// 暴露方法给父组件
defineExpose({
  syncContent() {
    syncContent();
    return editMode.value === 'markdown' ? markdownContent.value : 
           turndownService.turndown(editor.value?.getHTML() || '');
  },
  getContent() {
    return editMode.value === 'markdown' ? markdownContent.value : 
           turndownService.turndown(editor.value?.getHTML() || '');
  },
  setContent(content: string) {
    if (editor.value) {
      const html = isHTML(content) ? content : md.render(content);
      editor.value.commands.setContent(html);
      htmlContent.value = html;
      markdownContent.value = isHTML(content) ? turndownService.turndown(content) : content;
    }
  }
});
</script>

<style scoped>
.simple-html-editor {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.editor-tips {
  padding: 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.editor-tips :deep(.el-alert) {
  background: transparent;
  border: none;
  padding: 0;
}

.editor-tips p {
  margin: 4px 0;
  font-size: 14px;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.visual-editor {
  min-height: 400px;
}

.code-editor {
  padding: 16px;
}

.code-editor :deep(.el-textarea__inner) {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.6;
  border: none;
  box-shadow: none;
  resize: vertical;
}

/* TipTap编辑器样式 */
:deep(.ProseMirror) {
  padding: 16px;
  min-height: 400px;
  outline: none;
  font-size: 16px;
  line-height: 1.6;
}

:deep(.ProseMirror p) {
  margin: 1em 0;
}

:deep(.ProseMirror h1),
:deep(.ProseMirror h2),
:deep(.ProseMirror h3),
:deep(.ProseMirror h4),
:deep(.ProseMirror h5),
:deep(.ProseMirror h6) {
  margin: 1.5em 0 0.5em 0;
  font-weight: 600;
  color: #1f2937;
}

:deep(.ProseMirror ol),
:deep(.ProseMirror ul) {
  padding-left: 2em;
  margin: 1em 0;
}

:deep(.ProseMirror li) {
  margin: 0.5em 0;
}

:deep(.ProseMirror pre) {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 16px;
  margin: 1em 0;
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}

:deep(.ProseMirror code) {
  background: #f1f5f9;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9em;
}

:deep(.ProseMirror blockquote) {
  border-left: 4px solid #e5e7eb;
  padding-left: 16px;
  margin: 1em 0;
  color: #6b7280;
}

/* 预览样式 */
.preview-content {
  max-height: 60vh;
  overflow-y: auto;
  padding: 16px;
  line-height: 1.6;
  color: #374151;
}

.preview-content h1,
.preview-content h2,
.preview-content h3,
.preview-content h4,
.preview-content h5,
.preview-content h6 {
  margin: 1.5em 0 0.5em 0;
  font-weight: 600;
  color: #1f2937;
}

.preview-content p {
  margin: 1em 0;
}

.preview-content ol,
.preview-content ul {
  padding-left: 2em;
  margin: 1em 0;
}

.preview-content li {
  margin: 0.5em 0;
}

.preview-content pre {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  margin: 1em 0;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}

.preview-content code {
  background: #f1f5f9;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9em;
}

.preview-content pre code {
  background: none;
  padding: 0;
}

.preview-content blockquote {
  border-left: 4px solid #e5e7eb;
  padding-left: 16px;
  margin: 1em 0;
  color: #6b7280;
}
</style>