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
          <el-option label="VS Light" value="light" />
          <el-option label="VS Dark" value="dark" />
          <el-option label="GitHub" value="github" />
          <el-option label="Monokai" value="monokai" />
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
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { Editor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import { createLowlight } from 'lowlight';
import MarkdownIt from 'markdown-it';
import TurndownService from 'turndown';

// 导入常用语言
import javascript from 'highlight.js/lib/languages/javascript';
import python from 'highlight.js/lib/languages/python';
import css from 'highlight.js/lib/languages/css';
import html from 'highlight.js/lib/languages/xml';
import json from 'highlight.js/lib/languages/json';
import bash from 'highlight.js/lib/languages/bash';
import java from 'highlight.js/lib/languages/java';
import cpp from 'highlight.js/lib/languages/cpp';
import typescript from 'highlight.js/lib/languages/typescript';

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
const currentTheme = ref('light');
const editor = ref<Editor | null>(null);
const previewHtml = ref('');

// 创建lowlight实例
const lowlight = createLowlight();

// 注册语言
lowlight.register('javascript', javascript);
lowlight.register('python', python);
lowlight.register('css', css);
lowlight.register('html', html);
lowlight.register('json', json);
lowlight.register('bash', bash);
lowlight.register('java', java);
lowlight.register('cpp', cpp);
lowlight.register('typescript', typescript);

// Markdown 解析器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: false,
  xhtmlOut: false
});

// Turndown 服务
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
function createEditor() {
  try {
    editor.value = new Editor({
      extensions: [
        StarterKit.configure({
          codeBlock: false, // 禁用默认代码块
        }),
        CodeBlockLowlight.configure({
          lowlight,
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
    
    console.log('编辑器创建成功，使用CodeBlockLowlight扩展');
  } catch (error) {
    console.error('创建编辑器失败:', error);
  }
}

// HTML 转 Markdown
function toMarkdownFromHTML(html: string): string {
  try {
    return turndownService.turndown(html).trim();
  } catch (error) {
    console.error('HTML转Markdown失败:', error);
    return html;
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
  
  const { state, dispatch } = editor.value.view;
  const { doc } = state;
  
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
function handleThemeChange() {
  console.log(`切换主题为: ${currentTheme.value}`);
  // 主题切换会通过CSS类来实现
  document.documentElement.className = `theme-${currentTheme.value}`;
}

// 监听 props 变化
watch(() => props.modelValue, (newValue) => {
  if (editor.value && newValue !== toMarkdownFromHTML(editor.value.getHTML())) {
    editor.value.commands.setContent(md.render(newValue));
  }
});

// 生命周期
onMounted(() => {
  createEditor();
  updatePreview();
  // 设置初始主题
  document.documentElement.className = `theme-${currentTheme.value}`;
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

/* 基础编辑器样式 */
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

:deep(.ProseMirror ul) {
  list-style-type: disc;
  padding-left: 2em;
  margin: 1em 0;
}

:deep(.ProseMirror ul li) {
  margin: 0.5em 0;
}

/* 代码块样式 */
:deep(.ProseMirror pre) {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 16px;
  margin: 1em 0;
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}

:deep(.ProseMirror pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
  font-size: 14px;
  color: #374151;
}

:deep(.ProseMirror code) {
  background: #f1f5f9;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9em;
}

/* 预览区域样式 */
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
</style>

<!-- 全局主题样式 -->
<style>
/* Light主题 - highlight.js样式 */
.theme-light .hljs {
  color: #24292e;
  background: #f8f9fa;
}

.theme-light .hljs-keyword,
.theme-light .hljs-selector-tag,
.theme-light .hljs-meta {
  color: #d73a49;
  font-weight: 600;
}

.theme-light .hljs-string,
.theme-light .hljs-doctag {
  color: #032f62;
}

.theme-light .hljs-comment,
.theme-light .hljs-quote {
  color: #6a737d;
  font-style: italic;
}

.theme-light .hljs-number,
.theme-light .hljs-literal {
  color: #005cc5;
}

.theme-light .hljs-function {
  color: #6f42c1;
}

/* Dark主题 - highlight.js样式 */
.theme-dark .hljs {
  color: #e1e4e8;
  background: #2d3748;
}

.theme-dark .hljs-keyword,
.theme-dark .hljs-selector-tag,
.theme-dark .hljs-meta {
  color: #ff7b72;
  font-weight: 600;
}

.theme-dark .hljs-string,
.theme-dark .hljs-doctag {
  color: #a5d6ff;
}

.theme-dark .hljs-comment,
.theme-dark .hljs-quote {
  color: #8b949e;
  font-style: italic;
}

.theme-dark .hljs-number,
.theme-dark .hljs-literal {
  color: #79c0ff;
}

.theme-dark .hljs-function {
  color: #d2a8ff;
}

/* GitHub主题 */
.theme-github .hljs {
  color: #24292f;
  background: #f6f8fa;
}

.theme-github .hljs-keyword {
  color: #cf222e;
  font-weight: 600;
}

.theme-github .hljs-string {
  color: #0a3069;
}

.theme-github .hljs-comment {
  color: #6e7781;
  font-style: italic;
}

/* Monokai主题 */
.theme-monokai .hljs {
  color: #f8f8f2;
  background: #272822;
}

.theme-monokai .hljs-keyword {
  color: #f92672;
  font-weight: 600;
}

.theme-monokai .hljs-string {
  color: #e6db74;
}

.theme-monokai .hljs-comment {
  color: #75715e;
  font-style: italic;
}

.theme-monokai .hljs-function {
  color: #a6e22e;
}

/* 调整编辑器内的代码块背景 */
.theme-dark :deep(.ProseMirror pre) {
  background: #2d3748;
  border-color: #4a5568;
}

.theme-dark :deep(.ProseMirror pre code) {
  color: #e1e4e8;
}

.theme-monokai :deep(.ProseMirror pre) {
  background: #272822;
  border-color: #49483e;
}

.theme-monokai :deep(.ProseMirror pre code) {
  color: #f8f8f2;
}
</style>