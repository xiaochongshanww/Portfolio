<template>
  <div class="block-editor-container">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button-group>
          <el-button 
            size="small" 
            :type="mode === 'edit' ? 'primary' : ''" 
            @click="mode = 'edit'"
          >
            编辑
          </el-button>
          <el-button 
            size="small" 
            :type="mode === 'preview' ? 'primary' : ''" 
            @click="mode = 'preview'"
          >
            预览
          </el-button>
        </el-button-group>
      </div>
      
      <div class="toolbar-right">
        <el-select 
          v-model="globalLanguage" 
          placeholder="全局语言设置"
          size="small"
          style="width: 140px"
          @change="handleGlobalLanguageChange"
        >
          <el-option label="自动检测" value="auto" />
          <el-option label="Python" value="python" />
          <el-option label="JavaScript" value="javascript" />
          <el-option label="TypeScript" value="typescript" />
          <el-option label="HTML" value="html" />
          <el-option label="CSS" value="css" />
          <el-option label="JSON" value="json" />
          <el-option label="Bash" value="bash" />
          <el-option label="Java" value="java" />
          <el-option label="C++" value="cpp" />
          <el-option label="纯文本" value="plaintext" />
        </el-select>
        
        <el-select 
          v-model="currentTheme" 
          placeholder="主题"
          size="small"
          style="width: 120px"
          @change="handleThemeChange"
        >
          <el-option label="VS Code Light" value="light-plus" />
          <el-option label="VS Code Dark" value="dark-plus" />
          <el-option label="GitHub Light" value="github-light" />
          <el-option label="GitHub Dark" value="github-dark" />
          <el-option label="Monokai" value="monokai" />
          <el-option label="Dracula" value="dracula" />
        </el-select>
      </div>
    </div>

    <!-- 编辑器内容 -->
    <div v-show="mode === 'edit'" class="editor-container">
      <editor-content :editor="editor" />
    </div>
    
    <!-- 预览内容 -->
    <div v-show="mode === 'preview'" class="preview-container">
      <div v-html="previewHtml" class="preview-content"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { Editor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import CodeBlockShiki from 'tiptap-extension-code-block-shiki';
import MarkdownIt from 'markdown-it';
import TurndownService from 'turndown';

// Props 和 Emits
interface Props {
  modelValue: string;
}

interface Emits {
  (e: 'update:modelValue', value: string): void;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: ''
});

const emit = defineEmits<Emits>();

// 响应式数据
const mode = ref<'edit' | 'preview'>('edit');
const globalLanguage = ref('auto');
const currentTheme = ref('light-plus');
const editor = ref<Editor | null>(null);
const previewHtml = ref('');

// Markdown 解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: false,
  xhtmlOut: false
});

// Turndown 服务 (HTML -> Markdown)
const turndownService = new TurndownService({
  headingStyle: 'atx',
  bulletListMarker: '-',
  codeBlockStyle: 'fenced',
  fence: '```'
});

// 配置 turndown 规则
turndownService.addRule('codeBlock', {
  filter: function (node) {
    return node.nodeName === 'PRE' && node.firstChild && node.firstChild.nodeName === 'CODE';
  },
  replacement: function (content, node) {
    const codeElement = node.firstChild as HTMLElement;
    const language = codeElement.className.replace('language-', '') || '';
    return '\n```' + language + '\n' + content + '\n```\n';
  }
});

// 创建编辑器
async function createEditor() {
  try {
    editor.value = new Editor({
      extensions: [
        StarterKit.configure({
          codeBlock: false, // 禁用默认的代码块
        }),
        CodeBlockShiki.configure({
          defaultTheme: currentTheme.value,
          defaultLanguage: globalLanguage.value === 'auto' ? null : globalLanguage.value,
        }),
      ],
      content: props.modelValue ? md.render(props.modelValue) : '<p></p>',
      onUpdate: ({ editor }) => {
        const markdown = toMarkdownFromHTML(editor.getHTML());
        emit('update:modelValue', markdown);
        updatePreview();
      },
    });
    
    console.log('编辑器创建成功，支持的扩展:', editor.value.extensionManager.extensions.map(ext => ext.name));
  } catch (error) {
    console.error('创建编辑器失败:', error);
    
    // 降级到基础CodeBlock
    editor.value = new Editor({
      extensions: [
        StarterKit, // 使用默认配置，包含基础CodeBlock
      ],
      content: props.modelValue ? md.render(props.modelValue) : '<p></p>',
      onUpdate: ({ editor }) => {
        const markdown = toMarkdownFromHTML(editor.getHTML());
        emit('update:modelValue', markdown);
        updatePreview();
      },
    });
    
    console.warn('已降级到基础CodeBlock扩展');
  }
}

// HTML 转 Markdown (使用 Turndown)
function toMarkdownFromHTML(html: string): string {
  try {
    return turndownService.turndown(html).trim();
  } catch (error) {
    console.error('HTML转Markdown失败:', error);
    return html; // 降级处理
  }
}

// 更新预览
function updatePreview() {
  if (editor.value) {
    const markdown = toMarkdownFromHTML(editor.value.getHTML());
    previewHtml.value = md.render(markdown);
  }
}

// 处理全局语言变化
function handleGlobalLanguageChange() {
  if (!editor.value) return;
  
  console.log(`设置全局语言为: ${globalLanguage.value}`);
  
  // 使用 Shiki 扩展的内置方法来更新所有代码块
  const { state, dispatch } = editor.value.view;
  const { doc } = state;
  
  // 查找所有代码块节点并更新语言
  let tr = state.tr;
  let updated = false;
  
  doc.descendants((node, pos) => {
    if (node.type.name === 'codeBlock') {
      const newAttrs = {
        ...node.attrs,
        language: globalLanguage.value === 'auto' ? null : globalLanguage.value
      };
      
      if (JSON.stringify(node.attrs) !== JSON.stringify(newAttrs)) {
        tr = tr.setNodeMarkup(pos, undefined, newAttrs);
        updated = true;
      }
    }
  });
  
  if (updated) {
    dispatch(tr);
    console.log(`已更新所有代码块语言为: ${globalLanguage.value}`);
  }
}

// 处理主题变化
async function handleThemeChange() {
  console.log(`切换主题为: ${currentTheme.value}`);
  
  // 重新创建编辑器以应用新主题
  if (editor.value) {
    const content = editor.value.getHTML();
    editor.value.destroy();
    
    await nextTick();
    await createEditor();
    if (editor.value) {
      editor.value.commands.setContent(content);
    }
  }
}

// 监听 props 变化
watch(() => props.modelValue, (newValue) => {
  if (editor.value && newValue !== toMarkdownFromHTML(editor.value.getHTML())) {
    editor.value.commands.setContent(md.render(newValue));
  }
});

// 生命周期
onMounted(async () => {
  await createEditor();
  updatePreview();
});

onBeforeUnmount(() => {
  if (editor.value) {
    editor.value.destroy();
  }
});

// 暴露方法给父组件
defineExpose({
  syncContent() {
    if (editor.value) {
      return toMarkdownFromHTML(editor.value.getHTML());
    }
    return '';
  },
  getContent() {
    if (editor.value) {
      return toMarkdownFromHTML(editor.value.getHTML());
    }
    return '';
  },
  setContent(content: string) {
    if (editor.value) {
      editor.value.commands.setContent(md.render(content));
    }
  }
});
</script>

<style scoped>
.block-editor-container {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.editor-container {
  min-height: 400px;
}

.preview-container {
  min-height: 400px;
  padding: 16px;
  background: white;
}

.preview-content {
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

.preview-content pre {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  margin: 1em 0;
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

/* TipTap 编辑器样式 */
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

:deep(.ProseMirror pre) {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 16px;
  margin: 1em 0;
  overflow-x: auto;
  border: 1px solid #e5e7eb;
}

:deep(.ProseMirror code) {
  background: #f1f5f9;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9em;
}

:deep(.ProseMirror pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
}

/* 有序列表样式修复 */
:deep(.ProseMirror ol) {
  counter-reset: list-counter;
  list-style: none;
  padding-left: 2em;
  margin: 1em 0;
}

:deep(.ProseMirror ol li) {
  counter-increment: list-counter;
  position: relative;
  margin: 0.5em 0;
}

:deep(.ProseMirror ol li::before) {
  content: counter(list-counter) ".";
  position: absolute;
  left: -2em;
  width: 1.5em;
  text-align: right;
  font-weight: 500;
  color: #6b7280;
}

/* 无序列表样式 */
:deep(.ProseMirror ul) {
  list-style-type: disc;
  padding-left: 2em;
  margin: 1em 0;
}

:deep(.ProseMirror ul li) {
  margin: 0.5em 0;
}

/* 预览区域的列表样式 */
.preview-content ol {
  counter-reset: list-counter;
  list-style: none;
  padding-left: 2em;
  margin: 1em 0;
}

.preview-content ol li {
  counter-increment: list-counter;
  position: relative;
  margin: 0.5em 0;
}

.preview-content ol li::before {
  content: counter(list-counter) ".";
  position: absolute;
  left: -2em;
  width: 1.5em;
  text-align: right;
  font-weight: 500;
  color: #6b7280;
}

.preview-content ul {
  list-style-type: disc;
  padding-left: 2em;
  margin: 1em 0;
}

.preview-content ul li {
  margin: 0.5em 0;
}

/* Shiki 会自动处理语法高亮样式 */
/* 如果Shiki未加载，提供基础代码高亮样式 */
:deep(.ProseMirror pre code .hljs-keyword) {
  color: #d73a49;
  font-weight: 600;
}

:deep(.ProseMirror pre code .hljs-string) {
  color: #032f62;
}

:deep(.ProseMirror pre code .hljs-comment) {
  color: #6a737d;
  font-style: italic;
}
</style>