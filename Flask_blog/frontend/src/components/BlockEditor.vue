<template>
  <div class="modern-editor">
    <!-- 编辑器工具栏 -->
    <div class="editor-toolbar">
      <!-- 文本格式化组 -->
      <div class="toolbar-group">
        <el-tooltip content="粗体 (Ctrl+B)" placement="top">
          <el-button 
            @click="cmd('bold')" 
            :type="isActive('bold') ? 'primary' : 'default'"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><Edit /></el-icon>
          </el-button>
        </el-tooltip>
        
        <el-tooltip content="斜体 (Ctrl+I)" placement="top">
          <el-button 
            @click="cmd('italic')" 
            :type="isActive('italic') ? 'primary' : 'default'"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><EditPen /></el-icon>
          </el-button>
        </el-tooltip>
        
        <el-tooltip content="删除线" placement="top">
          <el-button 
            @click="cmd('strike')" 
            :type="isActive('strike') ? 'primary' : 'default'"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 标题组 -->
      <div class="toolbar-group">
        <el-tooltip content="大标题 (H2)" placement="top">
          <el-button 
            @click="toggleHeading(2)" 
            :type="isHeading(2) ? 'primary' : 'default'"
            size="small"
            class="toolbar-btn"
          >
            H2
          </el-button>
        </el-tooltip>
        
        <el-tooltip content="小标题 (H3)" placement="top">
          <el-button 
            @click="toggleHeading(3)" 
            :type="isHeading(3) ? 'primary' : 'default'"
            size="small"
            class="toolbar-btn"
          >
            H3
          </el-button>
        </el-tooltip>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 列表组 -->
      <div class="toolbar-group">
        <el-tooltip content="无序列表" placement="top">
          <el-button 
            @click="cmd('bullet')" 
            :type="isActive('bulletList') ? 'primary' : 'default'"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><List /></el-icon>
          </el-button>
        </el-tooltip>
        
        <el-tooltip content="有序列表" placement="top">
          <el-button 
            @click="cmd('ordered')" 
            :type="isActive('orderedList') ? 'primary' : 'default'"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><FolderOpened /></el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 插入内容组 -->
      <div class="toolbar-group">
        <el-tooltip content="插入图片" placement="top">
          <el-button 
            @click="insertImageDialog"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><Picture /></el-icon>
          </el-button>
        </el-tooltip>
        
        <el-tooltip content="代码块" placement="top">
          <el-button 
            @click="cmd('codeblock')" 
            :type="isActive('codeBlock') ? 'primary' : 'default'"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><Document /></el-icon>
          </el-button>
        </el-tooltip>
        
        
        <!-- 主题选择器 -->
        <el-tooltip content="代码主题" placement="top">
          <el-dropdown @command="handleThemeChange" size="small" class="theme-dropdown">
            <el-button size="small" class="toolbar-btn">
              <el-icon><Brush /></el-icon>
              <span style="margin-left: 4px; font-size: 0.75rem;">主题</span>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="theme in codeThemes"
                  :key="theme.value"
                  :command="theme.value"
                  :class="{ 'is-active': currentCodeTheme === theme.value }"
                >
                  <div class="theme-option">
                    <span class="theme-name">{{ theme.label }}</span>
                    <div class="theme-preview" :style="{ background: theme.preview }"></div>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-tooltip>
        
        <el-tooltip content="插入链接" placement="top">
          <el-button 
            @click="insertLinkDialog"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><Link /></el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <div class="toolbar-divider"></div>

      <!-- 高级功能组 -->
      <div class="toolbar-group">
        <el-tooltip content="插入视频" placement="top">
          <el-button 
            @click="openVideoDialog"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><VideoPlay /></el-icon>
          </el-button>
        </el-tooltip>
        
        <el-tooltip content="插入 GitHub Gist" placement="top">
          <el-button 
            @click="openGistDialog"
            size="small"
            class="toolbar-btn"
          >
            <el-icon><DocumentCopy /></el-icon>
          </el-button>
        </el-tooltip>
        
        <!-- 全文代码语言设置 -->
        <el-tooltip content="设置全文代码语言" placement="top">
          <el-dropdown @command="handleGlobalLanguageChange" size="small" class="global-lang-dropdown">
            <el-button size="small" class="toolbar-btn">
              <el-icon><DataLine /></el-icon>
              <span style="margin-left: 4px; font-size: 0.75rem;">全局语言</span>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="lang in supportedLanguages"
                  :key="lang.value"
                  :command="lang.value"
                >
                  <span>{{ lang.label }}</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-tooltip>
      </div>

      <!-- 右侧工具组 -->
      <div class="toolbar-spacer"></div>
      <div class="toolbar-group">
        <div class="word-count">
          字数: <span class="count-number">{{ wordCount }}</span>
        </div>
        <div class="reading-time">
          阅读: <span class="time-number">{{ readingTime }}分钟</span>
        </div>
      </div>
    </div>

    <!-- 编辑器内容区域 -->
    <div class="editor-container">
      <div ref="editorEl" class="editor-content" tabindex="0" @click="focusEditor($event)" />
      <div v-if="!props.modelValue" class="editor-placeholder">
        开始编写您的文章内容...
      </div>
    </div>

    <!-- 隐藏的文件输入 -->
    <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleFileChange" />

    <!-- 状态栏 -->
    <div class="editor-statusbar">
      <div class="statusbar-left">
        <span class="status-text">支持拖拽上传图片 · Markdown 格式</span>
      </div>
      <div class="statusbar-right">
        <el-button 
          size="small" 
          text 
          @click="togglePreview"
          class="preview-btn"
        >
          <el-icon><View /></el-icon>
          {{ showPreview ? '编辑' : '预览' }}
        </el-button>
      </div>
    </div>

    <!-- 插入链接对话框 -->
    <el-dialog
      v-model="linkDialogVisible"
      title="插入链接"
      width="400px"
      :before-close="closeLinkDialog"
    >
      <el-form :model="linkForm" label-position="top">
        <el-form-item label="链接文字">
          <el-input v-model="linkForm.text" placeholder="输入链接显示的文字" />
        </el-form-item>
        <el-form-item label="链接地址">
          <el-input v-model="linkForm.url" placeholder="https://example.com" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeLinkDialog">取消</el-button>
        <el-button type="primary" @click="insertLink">插入</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue';
import { Editor } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import Image from '@tiptap/extension-image';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import { common, createLowlight } from 'lowlight';
import Turndown from 'turndown';
import { mdToHtml, htmlToMd } from '../utils/editorConversion';
import api from '../apiClient';
import { ElMessage } from 'element-plus';
import { 
  Edit, EditPen, Delete, List, Setting, Picture, Paperclip, Link, 
  VideoPlay, DocumentCopy, View, Document, Brush, Refresh,
  DataLine, FolderOpened
} from '@element-plus/icons-vue';
import { 
  codeThemes, 
  currentTheme, 
  switchTheme, 
  initTheme,
  updateGlobalCodeTheme 
} from '../utils/codeTheme';

// 创建 lowlight 实例，包含常用语言
const lowlight = createLowlight(common);

// 注册额外的语言支持
import javascript from 'highlight.js/lib/languages/javascript';
import python from 'highlight.js/lib/languages/python';
import css from 'highlight.js/lib/languages/css';
import xml from 'highlight.js/lib/languages/xml';

lowlight.register('javascript', javascript);
lowlight.register('python', python);
lowlight.register('css', css);
lowlight.register('html', xml);

const props = defineProps({ modelValue: { type: String, default: '' } });
const emit = defineEmits(['update:modelValue','image-uploaded']);

// 暴露同步方法给父组件
defineExpose({
  syncContent() {
    if (editor) {
      updateModelFromEditor();
      return toMarkdownFromHTML(editor.getHTML());
    }
    return '';
  },
  getContent() {
    if (editor) {
      return toMarkdownFromHTML(editor.getHTML());
    }
    return '';
  }
});
const editorEl = ref(null);
let editor; // TipTap 实例
let languageChanging = false; // 语言切换中的标志
const turndownService = new Turndown({ headingStyle: 'atx', codeBlockStyle: 'fenced' });

// 新增响应式状态
const wordCount = ref(0);
const showPreview = ref(false);
const linkDialogVisible = ref(false);
const linkForm = ref({ text: '', url: '' });

// 主题相关状态
const currentCodeTheme = currentTheme;

// 计算阅读时间（基于中文250字/分钟，英文200词/分钟）
const readingTime = computed(() => {
  if (!wordCount.value) return 1;
  const estimatedMinutes = Math.ceil(wordCount.value / 200);
  return Math.max(1, estimatedMinutes);
});

async function uploadImage(file){
  const fd = new FormData(); fd.append('file', file);
  try {
    const r = await api.post('/api/v1/uploads/image', fd, { headers:{ 'Content-Type':'multipart/form-data' }});
    const meta = r.data?.data;
    if(meta){ editor.chain().focus().setImage({ src: meta.url, alt: 'image' }).run(); emit('image-uploaded', meta); }
  } catch(e){ console.error('upload failed', e); }
}
function handlePaste(e){
  const items = e.clipboardData?.items; if(!items) return;
  for(const it of items){ if(it.kind==='file'){ const f = it.getAsFile(); if(f && f.type.startsWith('image/')){ uploadImage(f); e.preventDefault(); break; } } }
}
function handleDrop(e){
  const files = e.dataTransfer?.files; if(!files) return;
  for(const f of files){ if(f.type.startsWith('image/')){ uploadImage(f); e.preventDefault(); break; } }
}
function toMarkdownFromHTML(html){ return htmlToMd(html || ''); }
function updateModelFromEditor(){ 
  const html = editor.getHTML(); 
  const md = toMarkdownFromHTML(html); 
  
  // 更新字数统计
  const textContent = editor.getText();
  wordCount.value = textContent.length;
  
  emit('update:modelValue', md); 
}

onMounted(()=>{
  // 初始化主题
  initTheme();
  
  const initialHTML = mdToHtml(props.modelValue || '');
  editor = new Editor({ 
    element: editorEl.value, 
    content: initialHTML, 
    extensions: [
      StarterKit.configure({
        codeBlock: false, // 禁用默认的 codeBlock，使用 CodeBlockLowlight 代替
      }),
      Image,
      CodeBlockLowlight.configure({
        lowlight,
        defaultLanguage: null, // 自动检测语言
        HTMLAttributes: {
          class: 'hljs code-block-with-lang', // 添加自定义类名
        },
        languageClassPrefix: 'hljs-',
        exitOnTripleEnter: false,
      }),
    ], 
    autofocus: false, 
    onUpdate(){ updateModelFromEditor(); },
    onBlur() {
      // 关键修复：在失去焦点时强制同步内容
      if (editor) {
        updateModelFromEditor();
        console.log('编辑器失去焦点，强制同步内容');
      }
    },
    onCreate({ editor }) {
      // 初始化字数统计
      const textContent = editor.getText();
      wordCount.value = textContent.length;
      
      // 初始化代码块语言选择器
      initCodeBlockLanguageSelector();
    },
    onUpdate({ editor, transaction }) {
      // 智能自动触发：使用防抖机制
      if (transaction.docChanged) {
        console.log('TipTap内容变化，准备检查代码块，languageChanging:', languageChanging);
        
        // 如果正在进行语言切换，跳过选择器更新
        if (languageChanging) {
          console.log('语言切换中，跳过延迟的选择器更新');
          return;
        }
        
        // 清除之前的定时器
        if (updateTimeout) {
          clearTimeout(updateTimeout);
        }
        
        // 设置新的定时器，500ms后检查代码块
        updateTimeout = setTimeout(() => {
          console.log('执行延迟的选择器更新');
          updateCodeBlockLanguageSelectors();
        }, 500);
      }
    }
  });
  editorEl.value.addEventListener('paste', handlePaste);
  editorEl.value.addEventListener('drop', handleDrop);
});

watch(()=>props.modelValue, (v)=>{ if(!editor) return; const currentMd = toMarkdownFromHTML(editor.getHTML()); if(v !== currentMd){ editor.commands.setContent(mdToHtml(v || ''), false); } });

// 工具栏命令
function cmd(action){ 
  if(!editor) return; 
  const ch = editor.chain().focus(); 
  switch(action){ 
    case 'bold': ch.toggleBold().run(); break; 
    case 'italic': ch.toggleItalic().run(); break; 
    case 'bullet': ch.toggleBulletList().run(); break; 
    case 'ordered': ch.toggleOrderedList().run(); break; 
    case 'codeblock': 
      ch.toggleCodeBlock().run(); 
      // 延迟添加语言选择器，确保代码块已创建
      console.log('代码块按钮被点击');
      setTimeout(() => {
        console.log('执行代码块按钮触发的选择器更新');
        updateCodeBlockLanguageSelectors();
      }, 300);
      break; 
  } 
  updateModelFromEditor(); 
}

function toggleHeading(level){ if(!editor) return; editor.chain().focus().toggleHeading({ level }).run(); updateModelFromEditor(); }
function isActive(name){ return editor?.isActive(name); }
function isHeading(level){ return editor?.isActive('heading',{ level }); }

// 图片上传对话
const fileInput = ref(null);
function insertImageDialog(){ fileInput.value?.click(); }
function handleFileChange(e){ const f = e.target.files?.[0]; if(f) uploadImage(f); e.target.value=''; }

// 短代码插入
function openVideoDialog(){ const url = window.prompt('视频链接 (YouTube / Bilibili / Vimeo)'); if(url) insertVideo(url); }
function openGistDialog(){ const url = window.prompt('Gist 链接或 raw 地址'); if(url) insertGist(url); }
function insertVideo(url){ editor.chain().focus().insertContent(`\n:::video ${url}:::\n`).run(); updateModelFromEditor(); }
function insertGist(url){ editor.chain().focus().insertContent(`\n:::gist ${url}:::\n`).run(); updateModelFromEditor(); }

// 链接对话框功能
function insertLinkDialog() {
  if (!editor) return;
  
  linkForm.value = { text: '', url: '' };
  
  // 如果有选中文本，作为链接文字
  const { from, to } = editor.state.selection;
  if (from !== to) {
    const selectedText = editor.state.doc.textBetween(from, to);
    linkForm.value.text = selectedText;
  }
  
  linkDialogVisible.value = true;
}

function closeLinkDialog() {
  linkDialogVisible.value = false;
  linkForm.value = { text: '', url: '' };
}

function insertLink() {
  if (!editor) return;
  
  if (!linkForm.value.url.trim()) {
    ElMessage.error('请输入链接地址');
    return;
  }
  
  const url = linkForm.value.url.trim();
  const text = linkForm.value.text.trim() || url;
  
  // 插入 Markdown 格式链接
  const linkMarkdown = `[${text}](${url})`;
  
  const { from, to } = editor.state.selection;
  if (from !== to && linkForm.value.text) {
    // 替换选中文本
    editor.chain().focus().deleteSelection().insertContent(linkMarkdown).run();
  } else {
    // 在光标位置插入
    editor.chain().focus().insertContent(linkMarkdown).run();
  }
  
  updateModelFromEditor();
  closeLinkDialog();
  ElMessage.success('链接已插入');
}

// 预览切换
function togglePreview() {
  showPreview.value = !showPreview.value;
  // 这里可以添加预览逻辑，暂时只是状态切换
  ElMessage.info(showPreview.value ? '预览模式开启' : '编辑模式');
}

function focusEditor(e){ 
  if(editor){ 
    // 检查是否点击的是代码块，如果是则不改变焦点位置
    if (e && e.target && (e.target.tagName === 'CODE' || e.target.closest('pre'))) {
      return; // 不改变焦点位置，避免滚动到底部
    }
    editor.commands.focus(); // 只聚焦，不改变光标位置
  } 
}

// 主题切换处理
function handleThemeChange(theme) {
  switchTheme(theme);
  ElMessage.success(`已切换到 ${codeThemes.find(t => t.value === theme)?.label} 主题`);
}

// 全文代码语言设置处理
function handleGlobalLanguageChange(language) {
  if (!editor) {
    ElMessage.warning('编辑器未初始化');
    return;
  }

  console.log(`开始批量设置所有代码块为语言: ${language}`);
  
  // 使用简单直接的DOM方法，避免TipTap事务冲突
  const codeBlocks = editorEl.value.querySelectorAll('pre');
  if (codeBlocks.length === 0) {
    ElMessage.info('当前文档中没有代码块');
    return;
  }

  let processedCount = 0;
  
  codeBlocks.forEach((pre, index) => {
    try {
      console.log(`处理第 ${index + 1} 个代码块`);
      
      // 直接更新DOM属性
      const oldLang = pre.dataset.language || 'undefined';
      pre.dataset.language = language === 'auto' ? '' : language;
      
      // 强制更新 pre 元素的 class 属性
      pre.className = `hljs code-block-with-lang${language !== 'auto' ? ' language-' + language : ''}`;
      
      console.log(`DEBUG: 代码块 ${index + 1} 语言更新: ${oldLang} -> ${pre.dataset.language}, class: ${pre.className}`);
      
      // 安全的语法高亮更新
      if (language !== 'auto') {
        const codeElement = pre.querySelector('code');
        if (codeElement) {
          try {
            const codeContent = codeElement.textContent;
            if (codeContent && codeContent.trim()) {
              // 使用 lowlight 重新高亮
              const result = lowlight.highlight(language, codeContent);
              
              // 安全地替换内容 - 关键修复：保存原内容防止数据丢失
              const originalContent = codeElement.textContent;
              
              try {
                const fragment = document.createDocumentFragment();
                
                // 检查 lowlight.highlight 返回的结果
                console.log('DEBUG: lowlight 结果类型:', typeof result, '结果:', result);
                
                if (result && result.children && result.children.length > 0) {
                  // lowlight 返回的是 virtual DOM 节点，不是真实 DOM
                  try {
                    // 直接使用 lowlight 的 toHtml 或者直接设置 innerHTML
                    if (result.value) {
                      codeElement.innerHTML = result.value;
                    } else {
                      // 安全降级：使用 lowlight.highlight 的 value 属性
                      if (result.value) {
                        codeElement.innerHTML = result.value;
                      } else {
                        console.log('DEBUG: lowlight 结果无 value，保持原内容');
                        codeElement.innerHTML = originalContent;
                      }
                    }
                  } catch (hlError) {
                    console.log('DEBUG: 使用原始 highlight.js 失败:', hlError);
                    // 最后的降级方案
                    codeElement.innerHTML = result.value || originalContent;
                  }
                  
                  // 只有在成功创建 fragment 后才清空并替换
                  if (fragment.children.length > 0) {
                    codeElement.innerHTML = '';
                    codeElement.appendChild(fragment);
                    
                    // 关键修复：确保 CSS 类名正确设置
                    codeElement.className = `hljs language-${language}`;
                    pre.className = `hljs code-block-with-lang language-${language}`;
                    
                  } else {
                    // 如果 fragment 为空，使用 innerHTML 直接设置
                    codeElement.innerHTML = result.value || originalContent;
                    codeElement.className = `hljs language-${language}`;
                    pre.className = `hljs code-block-with-lang language-${language}`;
                  }
                } else if (result && result.value) {
                  // 如果没有 children，但有 value，直接使用
                  codeElement.innerHTML = result.value;
                  codeElement.className = `hljs language-${language}`;
                  pre.className = `hljs code-block-with-lang language-${language}`;
                } else {
                  // 如果都没有，保持原内容
                  console.log('语法高亮结果为空，保持原内容');
                }
              } catch (replaceError) {
                console.error('替换内容时出错，保持原内容:', replaceError);
                // 出错时保持原内容
                if (codeElement.textContent !== originalContent) {
                  codeElement.textContent = originalContent;
                }
              }
              
              console.log(`代码块 ${index + 1} 语法高亮更新完成: ${language}`);
              
              // 关键修复：强制刷新CSS样式，特别是Python高亮
              if (language === 'python') {
                console.log(`DEBUG: 全局Python高亮修复开始 - 代码块 ${index + 1}`);
                console.log('DEBUG: 修复前 codeElement.className:', codeElement.className);
                console.log('DEBUG: 修复前 pre.className:', pre.className);
                
                // 触发重绘，确保Python关键字高亮生效
                pre.style.display = 'none';
                pre.offsetHeight; // 强制重绘
                pre.style.display = 'block';
                
                // 双重保险：延迟再次确认CSS类名
                setTimeout(() => {
                  console.log('DEBUG: 延迟检查 codeElement.className:', codeElement.className);
                  if (codeElement.className.indexOf('language-python') === -1) {
                    codeElement.className = `hljs language-python`;
                    pre.className = `hljs code-block-with-lang language-python`;
                    console.log('DEBUG: 重新设置全局Python CSS类名');
                  }
                  
                  // 检查import关键字高亮状态
                  const importKeywords = codeElement.querySelectorAll('.hljs-keyword');
                  let importFound = false;
                  importKeywords.forEach((kw, kwIdx) => {
                    if (kw.textContent.trim() === 'import') {
                      importFound = true;
                      const computedStyle = window.getComputedStyle(kw);
                      console.log(`DEBUG: 全局设置 import关键字 ${kwIdx} 样式:`, {
                        color: computedStyle.color,
                        backgroundColor: computedStyle.backgroundColor,
                        className: kw.className
                      });
                    }
                  });
                  if (!importFound) {
                    console.log('DEBUG: 全局设置后未找到import关键字');
                  }
                  
                  // Ultra fix: 强制应用主题样式
                  updateGlobalCodeTheme(currentTheme.value, editorEl.value);
                  
                  // Ultimate fix: 重新执行语法高亮确保正确性
                  setTimeout(async () => {
                    try {
                      const finalContent = codeElement.textContent;
                      console.log('DEBUG: Ultimate fix - 开始重新高亮 Python 代码');
                      
                      // 使用原始 highlight.js 确保兼容性
                      try {
                        const hljs = await import('highlight.js');
                        const highlighted = hljs.default.highlight(finalContent, { language: 'python' });
                        
                        codeElement.innerHTML = highlighted.value;
                        codeElement.className = 'hljs language-python';
                        pre.className = 'hljs code-block-with-lang language-python';
                        
                        console.log('DEBUG: Ultimate fix - 使用原始 highlight.js 成功');
                      } catch (hlError) {
                        console.log('DEBUG: 原始 highlight.js 失败，尝试 lowlight:', hlError);
                        
                        // 降级使用 lowlight
                        const newResult = lowlight.highlight('python', finalContent);
                        if (newResult && newResult.value) {
                          codeElement.innerHTML = newResult.value;
                        }
                        codeElement.className = 'hljs language-python';
                        pre.className = 'hljs code-block-with-lang language-python';
                      }
                      
                      // 终极修复：强制应用 import 关键字样式
                      setTimeout(() => {
                        const keywords = codeElement.querySelectorAll('.hljs-keyword');
                        keywords.forEach((keyword, kwIdx) => {
                          if (keyword.textContent.trim() === 'import') {
                            const color = currentTheme.value === 'dark' ? '#c678dd' : '#a626a4';
                            keyword.style.setProperty('color', color, 'important');
                            keyword.style.setProperty('font-weight', '500', 'important');
                            console.log(`DEBUG: 终极修复 - 强制设置 import ${kwIdx} 样式:`, color);
                          }
                        });
                        
                        // 终极Python关键字修复机制
                        const applyPythonKeywordFix = () => {
                          const color = currentTheme.value === 'dark' ? '#c678dd' : '#a626a4';
                          
                          // 1. 更新或创建全局CSS规则
                          let existingStyle = document.getElementById('python-import-fix');
                          if (existingStyle) {
                            existingStyle.remove();
                          }
                          
                          const style = document.createElement('style');
                          style.id = 'python-import-fix';
                          style.textContent = `
                            /* Python关键字样式 - 多重选择器覆盖 */
                            .hljs.language-python .hljs-keyword,
                            .code-block-with-lang.language-python .hljs-keyword,
                            pre[data-language="python"] .hljs-keyword,
                            .language-python .hljs-keyword {
                              color: ${color} !important;
                              font-weight: 500 !important;
                            }
                            
                            /* 特殊处理import和from关键字 */
                            .hljs.language-python .hljs-keyword[data-keyword="import"],
                            .hljs.language-python .hljs-keyword[data-keyword="from"],
                            .language-python .hljs-keyword:contains("import"),
                            .language-python .hljs-keyword:contains("from") {
                              color: ${color} !important;
                              font-weight: 600 !important;
                            }
                          `;
                          document.head.appendChild(style);
                          
                          // 2. 直接强制设置所有Python关键字样式
                          const pythonBlocks = document.querySelectorAll('pre[data-language="python"], .language-python');
                          pythonBlocks.forEach((block, blockIdx) => {
                            const keywords = block.querySelectorAll('.hljs-keyword');
                            keywords.forEach((keyword, kwIdx) => {
                              const text = keyword.textContent.trim();
                              keyword.style.setProperty('color', color, 'important');
                              keyword.style.setProperty('font-weight', text === 'import' || text === 'from' ? '600' : '500', 'important');
                              
                              // 添加数据属性标记
                              if (text === 'import' || text === 'from') {
                                keyword.setAttribute('data-keyword', text);
                              }
                              
                              console.log(`DEBUG: Python关键字 "${text}" 在块 ${blockIdx + 1} 设置样式完成`);
                            });
                          });
                          
                          console.log(`DEBUG: Python关键字修复完成 - 处理了 ${pythonBlocks.length} 个Python代码块`);
                        };
                        
                        // 立即应用修复
                        applyPythonKeywordFix();
                        
                        // 延迟再次确保修复生效
                        setTimeout(applyPythonKeywordFix, 200);
                        setTimeout(applyPythonKeywordFix, 500);
                      }, 100);
                      
                      console.log('DEBUG: Ultimate fix 完成 - 重新高亮完成');
                    } catch (ultimateError) {
                      console.error('DEBUG: Ultimate fix 失败:', ultimateError);
                    }
                  }, 100);
                }, 50);
              }
            }
          } catch (highlightError) {
            console.error(`语法高亮更新失败:`, highlightError);
            // 保持原始内容不变
          }
        }
      }
      
      processedCount++;
    } catch (error) {
      console.error('设置代码块语言失败:', error);
    }
  });

  // 延迟刷新语言选择器 - 多重保险机制
  setTimeout(() => {
    updateCodeBlockLanguageSelectors();
    
    // 第一层：标准更新
    setTimeout(() => {
      updateAllSelectorsDisplay(language);
      
      // 第二层：强制DOM更新  
      setTimeout(() => {
        const selectors = document.querySelectorAll('.floating-lang-selector-container');
        console.log(`DEBUG: 强制同步 - 找到 ${selectors.length} 个选择器`);
        
        selectors.forEach((selector, idx) => {
          const button = selector.querySelector('.el-select__selected-label, .el-select__selected-item');
          const input = selector.querySelector('.el-select__input');
          const wrapper = selector.querySelector('.el-select__wrapper');
          
          if (button || input || wrapper) {
            const langObj = supportedLanguages.find(l => l.value === language) || { label: '自动检测' };
            
            // 更新所有可能的显示元素
            if (button) {
              const oldText = button.textContent;
              button.textContent = langObj.label;
              console.log(`DEBUG: 更新按钮文本 ${idx + 1}: ${oldText} -> ${langObj.label}`);
            }
            
            if (input) {
              input.value = langObj.label;
              console.log(`DEBUG: 更新输入框值 ${idx + 1}: -> ${langObj.label}`);
            }
            
            // 触发Vue响应式更新
            const changeEvent = new Event('change', { bubbles: true });
            selector.dispatchEvent(changeEvent);
          }
        });
        
        // 第三层：终极保险 - 延迟再次确认
        setTimeout(() => {
          const finalSelectors = document.querySelectorAll('.floating-lang-selector-container');
          console.log(`DEBUG: 终极确认 - 检查 ${finalSelectors.length} 个选择器状态`);
          
          finalSelectors.forEach((selector, idx) => {
            const displayElement = selector.querySelector('.el-select__selected-label, .el-select__selected-item, .el-select__input');
            if (displayElement) {
              const currentText = displayElement.textContent || displayElement.value;
              const expectedText = supportedLanguages.find(l => l.value === language)?.label || '自动检测';
              
              if (currentText !== expectedText) {
                console.warn(`DEBUG: 选择器 ${idx + 1} 未同步! 当前: "${currentText}", 期望: "${expectedText}"`);
                // 强制最后一次更新
                if (displayElement.tagName === 'INPUT') {
                  displayElement.value = expectedText;
                } else {
                  displayElement.textContent = expectedText;
                }
              } else {
                console.log(`DEBUG: 选择器 ${idx + 1} 同步成功: "${currentText}"`);
              }
            }
          });
        }, 500);
      }, 300);
    }, 200);
  }, 100);

  const langText = language === 'auto' ? '自动检测' : 
    supportedLanguages.find(l => l.value === language)?.label || language;
  
  ElMessage.success(`已设置 ${processedCount} 个代码块为 ${langText}`);
}

// 关键修复：更新所有语言选择器显示
function updateAllSelectorsDisplay(targetLanguage) {
  console.log(`开始更新所有选择器显示为: ${targetLanguage}`);
  
  const selectors = document.querySelectorAll('.floating-lang-selector-container');
  console.log(`找到 ${selectors.length} 个语言选择器`);
  
  selectors.forEach((selector, index) => {
    const labelElement = selector.querySelector('.el-select__selected-label');
    const dropdownItems = selector.querySelectorAll('.el-select-dropdown__item');
    
    if (labelElement) {
      // 更新主按钮显示文本
      const langInfo = supportedLanguages.find(l => l.value === targetLanguage);
      const displayText = langInfo ? langInfo.label : '自动检测';
      labelElement.textContent = displayText;
      console.log(`选择器 ${index + 1} 更新为: ${displayText}`);
    }
    
    // 更新下拉框中的选中状态
    dropdownItems.forEach(item => {
      const itemValue = item.dataset.value;
      item.classList.remove('is-selected');
      
      // 移除旧的勾选图标
      const oldCheckIcon = item.querySelector('.el-select__check-icon');
      if (oldCheckIcon) {
        oldCheckIcon.remove();
      }
      
      // 如果是当前选中的语言，添加选中状态和图标
      if (itemValue === targetLanguage) {
        item.classList.add('is-selected');
        const span = item.querySelector('span');
        if (span) {
          span.insertAdjacentHTML('afterend', '<i class="el-icon el-select__check-icon"><svg viewBox="0 0 1024 1024" width="14" height="14"><path d="M406.656 706.944L195.84 496.256a32 32 0 1 0-45.248 45.248l256 256 512-512a32 32 0 0 0-45.248-45.248L406.656 706.944z"></path></svg></i>');
        }
      }
    });
  });
  
  console.log(`已更新所有选择器显示`);
}

// 支持的语言列表
const supportedLanguages = [
  { value: 'auto', label: '自动检测' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'python', label: 'Python' },
  { value: 'css', label: 'CSS' },
  { value: 'html', label: 'HTML' },
  { value: 'json', label: 'JSON' },
  { value: 'bash', label: 'Bash' },
  { value: 'plaintext', label: '纯文本' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
  { value: 'go', label: 'Go' }
];

// 改变代码块语言
function changeCodeBlockLanguage(pre, language) {
  console.log('切换代码块语言:', { pre, language });
  
  if (!editor || !pre) {
    console.log('编辑器或代码块不存在');
    return;
  }
  
  // 设置语言切换标志
  languageChanging = true;
  console.log('设置 languageChanging = true');
  
  try {
    // 方法4: 使用editor命令来查找和更新代码块
    const { state } = editor.view;
    const { doc, selection } = state;
    
    console.log('尝试使用编辑器命令查找代码块');
    
    // 遍历文档中的所有节点，查找代码块
    let targetPos = null;
    let targetNode = null;
    
    doc.descendants((node, pos) => {
      console.log('检查节点:', node.type.name, '位置:', pos);
      
      // 检查是否是代码块节点（可能是codeBlock或其他名称）
      if (node.type.name === 'codeBlock' || node.type.name.toLowerCase().includes('code')) {
        console.log('找到代码相关节点:', node.type.name, node);
        
        // 尝试获取该位置的DOM节点
        try {
          const domPos = editor.view.domAtPos(pos);
          const domNode = domPos.node;
          
          console.log('DOM节点:', domNode);
          
          // 向上查找pre元素
          let currentElement = domNode.nodeType === 1 ? domNode : domNode.parentElement;
          while (currentElement && currentElement !== document.body) {
            console.log('检查元素:', currentElement.tagName, currentElement);
            
            if (currentElement.tagName === 'PRE' && currentElement === pre) {
              targetPos = pos;
              targetNode = node;
              console.log('找到匹配的代码块，位置:', pos, '节点:', node);
              return false; // 停止遍历
            }
            currentElement = currentElement.parentElement;
          }
        } catch (e) {
          console.log('检查节点时出错:', e);
        }
      }
    });
    
    if (targetPos !== null && targetNode) {
      console.log('使用找到的位置更新代码块语言');
      
      const tr = state.tr;
      const newAttrs = { language: language === 'auto' ? null : language };
      
      console.log('设置新属性:', newAttrs, '位置:', targetPos);
      
      // 使用setNodeMarkup更新节点属性
      tr.setNodeMarkup(targetPos, null, newAttrs);
      
      // 分发事务
      const newState = state.apply(tr);
      editor.view.updateState(newState);
      
      // 更新DOM属性
      pre.dataset.language = language === 'auto' ? '' : language;
      
      // 强制刷新语法高亮
      setTimeout(() => {
        // 方法1: 触发 lowlight 重新渲染
        const codeElement = pre.querySelector('code');
        if (codeElement && language !== 'auto') {
          try {
            // 获取代码内容
            const codeContent = codeElement.textContent;
            
            // 使用 lowlight 重新高亮
            const highlighted = lowlight.highlight(language, codeContent);
            
            // 清空并重新添加高亮内容
            codeElement.innerHTML = '';
            codeElement.appendChild(highlighted);
            
            // 关键修复：设置正确的CSS类名
            codeElement.className = `hljs language-${language}`;
            pre.className = `hljs code-block-with-lang language-${language}`;
            
            // 关键修复：Python语法高亮强制刷新
            if (language === 'python') {
              console.log('DEBUG: 单个Python高亮修复开始');
              console.log('DEBUG: 修复前 codeElement.className:', codeElement.className);
              console.log('DEBUG: 修复前 pre.className:', pre.className);
              
              // 触发重绘，确保Python关键字高亮生效
              pre.style.display = 'none';
              pre.offsetHeight; // 强制重绘
              pre.style.display = 'block';
              
              // 二次确认CSS类名设置
              setTimeout(() => {
                console.log('DEBUG: 延迟检查 codeElement.className:', codeElement.className);
                if (codeElement.className.indexOf('language-python') === -1) {
                  codeElement.className = `hljs language-python`;
                  pre.className = `hljs code-block-with-lang language-python`;
                  console.log('DEBUG: 重新设置单个Python CSS类名');
                }
                
                // 检查import关键字高亮状态
                const importKeywords = codeElement.querySelectorAll('.hljs-keyword');
                let importFound = false;
                importKeywords.forEach((kw, kwIdx) => {
                  if (kw.textContent.trim() === 'import') {
                    importFound = true;
                    const computedStyle = window.getComputedStyle(kw);
                    console.log(`DEBUG: 单个设置 import关键字 ${kwIdx} 样式:`, {
                      color: computedStyle.color,
                      backgroundColor: computedStyle.backgroundColor,
                      className: kw.className
                    });
                  }
                });
                if (!importFound) {
                  console.log('DEBUG: 单个设置后未找到import关键字');
                }
                
                // Ultra fix: 强制应用主题样式
                updateGlobalCodeTheme(currentTheme.value, editorEl.value);
                
                // Ultimate fix: 重新执行语法高亮确保正确性
                setTimeout(async () => {
                  try {
                    const finalContent = codeElement.textContent;
                    console.log('DEBUG: 单个 Ultimate fix - 开始重新高亮 Python 代码');
                    
                    // 使用原始 highlight.js 确保兼容性
                    try {
                      const hljs = await import('highlight.js');
                      const highlighted = hljs.default.highlight(finalContent, { language: 'python' });
                      
                      codeElement.innerHTML = highlighted.value;
                      codeElement.className = 'hljs language-python';
                      pre.className = 'hljs code-block-with-lang language-python';
                      
                      console.log('DEBUG: 单个 Ultimate fix - 使用原始 highlight.js 成功');
                    } catch (hlError) {
                      console.log('DEBUG: 单个原始 highlight.js 失败，尝试 lowlight:', hlError);
                      
                      // 降级使用 lowlight
                      const newResult = lowlight.highlight('python', finalContent);
                      if (newResult && newResult.value) {
                        codeElement.innerHTML = newResult.value;
                      }
                      codeElement.className = 'hljs language-python';
                      pre.className = 'hljs code-block-with-lang language-python';
                    }
                    
                    // 终极修复：强制应用 import 关键字样式
                    setTimeout(() => {
                      const keywords = codeElement.querySelectorAll('.hljs-keyword');
                      keywords.forEach((keyword, kwIdx) => {
                        if (keyword.textContent.trim() === 'import') {
                          const color = currentTheme.value === 'dark' ? '#c678dd' : '#a626a4';
                          keyword.style.setProperty('color', color, 'important');
                          keyword.style.setProperty('font-weight', '500', 'important');
                          console.log(`DEBUG: 单个终极修复 - 强制设置 import ${kwIdx} 样式:`, color);
                        }
                      });
                    }, 100);
                    
                    console.log('DEBUG: 单个 Ultimate fix 完成 - 重新高亮完成');
                  } catch (ultimateError) {
                    console.error('DEBUG: 单个 Ultimate fix 失败:', ultimateError);
                  }
                }, 100);
                
                console.log('DEBUG: 单个Python语法高亮强制刷新完成');
              }, 50);
            }
            
            console.log(`强制刷新 ${language} 语法高亮完成`);
          } catch (error) {
            console.log('强制刷新语法高亮失败:', error);
          }
        }
        
        // 方法2: 强制重新渲染编辑器内容
        editor.commands.blur();
        editor.commands.focus();
      }, 50);
      
      console.log('语言切换完成，已更新编辑器状态');
      
    } else {
      console.log('方法4也未能找到匹配的代码块');
      
      // 方法5: 尝试使用TipTap命令API
      console.log('尝试方法5：使用命令API');
      
      // 首先尝试聚焦到代码块
      const codeElement = pre.querySelector('code');
      if (codeElement) {
        try {
          // 创建一个范围来选择代码块内容
          const selection = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(codeElement);
          selection.removeAllRanges();
          selection.addRange(range);
          
          // 尝试使用编辑器命令更新代码块语言
          const success = editor.commands.updateAttributes('codeBlock', {
            language: language === 'auto' ? null : language
          });
          
          console.log('命令API更新结果:', success);
          
          if (success) {
            // 命令成功，更新DOM属性和选择器显示
            pre.dataset.language = language === 'auto' ? '' : language;
            
            // 强制刷新语法高亮
            setTimeout(() => {
              if (language !== 'auto') {
                try {
                  // 获取代码内容
                  const codeContent = codeElement.textContent;
                  
                  // 使用 lowlight 重新高亮
                  const highlighted = lowlight.highlight(language, codeContent);
                  
                  // 清空并重新添加高亮内容
                  codeElement.innerHTML = '';
                  codeElement.appendChild(highlighted);
                  
                  console.log(`强制刷新 ${language} 语法高亮完成 (方法5)`);
                } catch (error) {
                  console.log('强制刷新语法高亮失败 (方法5):', error);
                }
              }
            }, 50);
            
            // 更新选择器显示的语言
            const selector = document.querySelector(`.floating-lang-selector-container[data-code-block-id="${pre.dataset.codeBlockId}"]`);
            if (selector) {
              const selectedLabel = selector.querySelector('.el-select__selected-label');
              if (selectedLabel) {
                const langInfo = supportedLanguages.find(l => l.value === language);
                selectedLabel.textContent = langInfo ? langInfo.label : '自动检测';
                console.log('已更新选择器显示为:', selectedLabel.textContent);
              }
            }
            
            console.log('语言切换成功完成');
            
            // 延迟重置语言切换标志，确保TipTap内容更新完成
            setTimeout(() => {
              languageChanging = false;
              console.log('重置 languageChanging = false');
            }, 1000);
            
            return; // 成功了就不需要其他方法了
          } else {
            // 如果命令失败，尝试toggleCodeBlock
            console.log('尝试重新创建代码块');
            const content = codeElement.textContent;
            
            editor.commands.selectParentNode();
            editor.commands.toggleCodeBlock({
              language: language === 'auto' ? null : language
            });
            
            // 如果内容不同，重新设置
            if (editor.state.selection.$head.parent.textContent !== content) {
              editor.commands.insertContent(content);
            }
          }
          
        } catch (e) {
          console.log('命令API方法出错:', e);
        }
      }
      
      // 最后尝试：直接修改HTML（注释掉，因为会导致重新渲染问题）
      console.log('方法6：直接修改HTML已跳过，避免重新渲染');
      
      // 更新DOM属性
      pre.dataset.language = language === 'auto' ? '' : language;
      
      console.log('所有方法尝试完毕，语言切换可能已完成');
      
      // 延迟重置语言切换标志
      setTimeout(() => {
        languageChanging = false;
        console.log('重置 languageChanging = false (fallback)');
      }, 1000);
      
      // 注释掉HTML重新设置，因为这会导致整个编辑器重新渲染
      // 如果前面的命令API成功了，这里就不需要了
      /*
      // 获取当前HTML内容并修改
      let currentHtml = editor.getHTML();
      
      // 尝试替换pre标签的data-language属性
      const preRegex = /<pre([^>]*?)>/gi;
      currentHtml = currentHtml.replace(preRegex, (match, attrs) => {
        // 移除现有的data-language属性
        let newAttrs = attrs.replace(/\s*data-language="[^"]*"/gi, '');
        // 添加新的语言属性
        if (language !== 'auto') {
          newAttrs += ` data-language="${language}"`;
        }
        return `<pre${newAttrs}>`;
      });
      
      console.log('修改后的HTML片段:', currentHtml.substring(0, 200));
      
      // 重新设置内容
      setTimeout(() => {
        editor.commands.setContent(currentHtml);
        console.log('已重新设置编辑器内容');
      }, 50);
      */
    }
    
  } catch (error) {
    console.error('切换语言时出错:', error);
    
    // 出错时也要重置标志
    setTimeout(() => {
      languageChanging = false;
      console.log('重置 languageChanging = false (error)');
    }, 1000);
  }
}

// 初始化代码块语言选择器
function initCodeBlockLanguageSelector() {
  // 初始化时自动为现有代码块添加选择器
  console.log('初始化语言选择器');
  setTimeout(() => {
    console.log('执行初始化的选择器更新');
    updateCodeBlockLanguageSelectors();
  }, 1000);
}

// 防抖变量
let updateTimeout = null;
let isUpdating = false;

// 手动更新所有代码块的语言选择器
function updateCodeBlockLanguageSelectors() {
  if (!editorEl.value) {
    console.log('编辑器元素不存在');
    return;
  }
  
  // 查找所有代码块
  const codeBlocks = editorEl.value.querySelectorAll('pre');
  console.log('自动检查：找到代码块数量:', codeBlocks.length);
  
  // 清理孤立的选择器（对应的代码块已被删除）
  cleanupOrphanedSelectors(codeBlocks);
  
  if (codeBlocks.length === 0) {
    console.log('没有代码块，跳过选择器创建');
    return;
  }
  
  performSelectorUpdate(codeBlocks);
}

// 清理孤立选择器的函数
function cleanupOrphanedSelectors(currentCodeBlocks) {
  const allSelectors = document.querySelectorAll('.floating-lang-selector-container');
  const currentBlockIds = Array.from(currentCodeBlocks).map(pre => pre.dataset.codeBlockId).filter(Boolean);
  
  allSelectors.forEach(selector => {
    const blockId = selector.dataset.codeBlockId;
    if (blockId && !currentBlockIds.includes(blockId)) {
      if (selector._cleanup) {
        selector._cleanup();
      } else {
        selector.remove();
      }
    }
  });
}

// 实际执行选择器更新的函数
function performSelectorUpdate(codeBlocks) {
  console.log('开始执行选择器更新，代码块数量:', codeBlocks.length);
  
  // 为每个代码块检查并创建选择器
  codeBlocks.forEach((pre, index) => {
    console.log(`处理代码块 ${index}:`, pre);
    
    // 为代码块生成唯一ID
    if (!pre.dataset.codeBlockId) {
      pre.dataset.codeBlockId = `code-block-${Date.now()}-${index}`;
      console.log(`为代码块 ${index} 分配ID:`, pre.dataset.codeBlockId);
    }
    
    // 检查是否已经有对应的选择器
    const existingSelector = document.querySelector(`.floating-lang-selector-container[data-code-block-id="${pre.dataset.codeBlockId}"]`);
    if (existingSelector) {
      console.log(`代码块 ${index} 已有选择器，更新位置，选择器:`, existingSelector);
      console.log('选择器是否在DOM中:', document.body.contains(existingSelector));
      console.log('选择器当前样式:', existingSelector.style.cssText);
      // 更新现有选择器的位置
      updateSelectorPosition(existingSelector, pre);
      return;
    }
    
    console.log(`为代码块 ${index} 创建新选择器`);
    
    // 确保代码块有相对定位
    pre.style.position = 'relative';
    
    // 检测当前语言
    const currentLang = detectCodeBlockLanguage(pre);
    console.log('检测到的当前语言:', currentLang, 'pre.dataset.language:', pre.dataset.language);
    
    // 如果检测到了语言但DOM属性没有设置，更新DOM属性
    if (currentLang !== 'auto' && (!pre.dataset.language || pre.dataset.language === 'undefined')) {
      pre.dataset.language = currentLang;
      console.log('更新pre元素的data-language属性为:', currentLang);
      
      // 如果检测到了具体语言，尝试触发TipTap更新
      if (editor && currentLang !== 'auto') {
        try {
          editor.commands.updateAttributes('codeBlock', {
            language: currentLang
          });
          console.log('已更新TipTap代码块语言属性为:', currentLang);
        } catch (e) {
          console.log('更新TipTap属性失败，但DOM已更新:', e);
        }
      }
    }
    
    // 创建悬浮的语言选择器容器
    const selectorId = `lang-selector-${Date.now()}-${index}`;
    
    // 创建选择器容器
    const selectorContainer = document.createElement('div');
    selectorContainer.id = selectorId;
    selectorContainer.className = 'floating-lang-selector-container';
    selectorContainer.dataset.codeBlockId = pre.dataset.codeBlockId;
    
    // 找到当前语言的显示文本
    const currentLangInfo = supportedLanguages.find(l => l.value === currentLang);
    const currentLangLabel = currentLangInfo ? currentLangInfo.label : '自动检测';
    console.log('选择器将显示语言:', currentLangLabel);
    
    // 创建更美观的选择器HTML结构
    selectorContainer.innerHTML = `
      <div class="el-select-styled">
        <div class="el-select__wrapper">
          <div class="el-select__selection">
            <span class="el-select__selected-label">${currentLangLabel}</span>
            <i class="el-icon el-select__caret el-select__suffix">
              <svg viewBox="0 0 1024 1024" width="14" height="14">
                <path d="M831.872 340.864 512 652.672 192.128 340.864a30.592 30.592 0 0 0-42.752 0 29.12 29.12 0 0 0 0 41.6L489.664 714.24a30.592 30.592 0 0 0 42.752 0l340.288-331.712a29.12 29.12 0 0 0 0-41.6 30.592 30.592 0 0 0-40.832 0z"></path>
              </svg>
            </i>
          </div>
        </div>
        <div class="el-select__dropdown" style="display: none;">
          <div class="el-scrollbar">
            <div class="el-select-dropdown__list">
              ${supportedLanguages.map(lang => `
                <div class="el-select-dropdown__item ${lang.value === currentLang ? 'is-selected' : ''}" data-value="${lang.value}">
                  <span>${lang.label}</span>
                  ${lang.value === currentLang ? '<i class="el-icon el-select__check-icon"><svg viewBox="0 0 1024 1024" width="14" height="14"><path d="M406.656 706.944L195.84 496.256a32 32 0 1 0-45.248 45.248l256 256 512-512a32 32 0 0 0-45.248-45.248L406.656 706.944z"></path></svg></i>' : ''}
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      </div>
    `;
    
    // 将选择器添加到 body
    document.body.appendChild(selectorContainer);
    console.log(`选择器 ${index} 已添加到DOM，ID:`, selectorId);
    
    // 添加交互功能
    const selectWrapper = selectorContainer.querySelector('.el-select__wrapper');
    const dropdown = selectorContainer.querySelector('.el-select__dropdown');
    const selectedLabel = selectorContainer.querySelector('.el-select__selected-label');
    const caretIcon = selectorContainer.querySelector('.el-select__caret');
    const dropdownItems = selectorContainer.querySelectorAll('.el-select-dropdown__item');
    
    // 将状态存储在DOM元素上，避免闭包问题
    selectorContainer._isDropdownOpen = false;
    selectorContainer._isToggling = false;
    
    // 使用mousedown而不是click事件来避免冲突
    selectWrapper.addEventListener('mousedown', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      console.log('选择器被点击，当前状态:', selectorContainer._isDropdownOpen);
      console.log('选择器ID:', selectorId);
      
      selectorContainer._isToggling = true;
      selectorContainer._isDropdownOpen = !selectorContainer._isDropdownOpen;
      
      if (selectorContainer._isDropdownOpen) {
        console.log('打开下拉框');
        dropdown.style.cssText = `
          display: block !important;
          visibility: visible !important;
          opacity: 1 !important;
          position: absolute !important;
          top: 100% !important;
          left: 0 !important;
          right: 0 !important;
          background: #ffffff !important;
          border: 1px solid #dcdfe6 !important;
          border-radius: 6px !important;
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12) !important;
          margin-top: 4px !important;
          z-index: 99999 !important;
          max-height: 200px !important;
          overflow: hidden !important;
          backdrop-filter: blur(8px) !important;
        `;
        caretIcon.style.transform = 'rotate(180deg)';
        selectWrapper.classList.add('is-focused');
      } else {
        console.log('关闭下拉框');
        dropdown.style.display = 'none';
        caretIcon.style.transform = 'rotate(0deg)';
        selectWrapper.classList.remove('is-focused');
      }
      
      // 重置标志
      setTimeout(() => {
        selectorContainer._isToggling = false;
      }, 50);
    });
    
    // 阻止默认的click事件
    selectWrapper.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
    
    // 全局点击监听器，但要避免在切换时触发
    const globalClickHandler = (e) => {
      if (selectorContainer._isToggling) {
        console.log('忽略切换期间的全局点击');
        return;
      }
      
      if (!selectorContainer.contains(e.target) && selectorContainer._isDropdownOpen) {
        console.log('外部点击，关闭下拉框，选择器ID:', selectorId);
        selectorContainer._isDropdownOpen = false;
        dropdown.style.display = 'none';
        caretIcon.style.transform = 'rotate(0deg)';
        selectWrapper.classList.remove('is-focused');
      }
    };
    
    // 使用捕获阶段来更早拦截事件
    document.addEventListener('click', globalClickHandler, true);
    
    // 为选项添加样式
    dropdownItems.forEach(item => {
      // 设置基础样式
      item.style.cssText = `
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding: 6px 8px !important;
        font-size: 12px !important;
        color: #606266 !important;
        cursor: pointer !important;
        transition: background-color 0.2s !important;
      `;
      
      // 悬停效果
      item.addEventListener('mouseenter', () => {
        if (!item.classList.contains('is-selected')) {
          item.style.backgroundColor = '#f5f7fa';
        }
      });
      
      item.addEventListener('mouseleave', () => {
        if (!item.classList.contains('is-selected')) {
          item.style.backgroundColor = 'transparent';
        }
      });
      
      // 点击选项
      item.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        const newLang = item.dataset.value;
        const newLabel = item.querySelector('span').textContent;
        
        // 更新显示
        selectedLabel.textContent = newLabel;
        
        // 更新选中状态样式
        dropdownItems.forEach(i => {
          i.classList.remove('is-selected');
          i.style.cssText = `
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding: 6px 8px !important;
            font-size: 12px !important;
            color: #606266 !important;
            cursor: pointer !important;
            transition: background-color 0.2s !important;
            background-color: transparent !important;
          `;
        });
        
        item.classList.add('is-selected');
        item.style.cssText = `
          display: flex !important;
          align-items: center !important;
          justify-content: space-between !important;
          padding: 6px 8px !important;
          font-size: 12px !important;
          color: #409eff !important;
          cursor: pointer !important;
          transition: background-color 0.2s !important;
          background-color: #ecf5ff !important;
        `;
        
        // 更新勾选图标
        dropdownItems.forEach(i => {
          const checkIcon = i.querySelector('.el-select__check-icon');
          if (checkIcon) checkIcon.remove();
        });
        
        // 重新构建选项的HTML，包含勾选图标
        item.innerHTML = `<span>${newLabel}</span><i class="el-icon el-select__check-icon" style="color: #409eff; font-size: 12px;"><svg viewBox="0 0 1024 1024" width="14" height="14"><path d="M406.656 706.944L195.84 496.256a32 32 0 1 0-45.248 45.248l256 256 512-512a32 32 0 0 0-45.248-45.248L406.656 706.944z"></path></svg></i>`;
        
        // 关闭下拉
        selectorContainer._isDropdownOpen = false;
        dropdown.style.display = 'none';
        caretIcon.style.transform = 'rotate(0deg)';
        selectWrapper.classList.remove('is-focused');
        
        // 触发语言变更
        changeCodeBlockLanguage(pre, newLang);
      });
    });
    
    // 定位函数
    function positionSelector() {
      const preRect = pre.getBoundingClientRect();
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
      
      if (preRect.width > 0 && preRect.height > 0) {
        const top = preRect.top + scrollTop + 8;
        const left = preRect.right + scrollLeft - 120;
        
        selectorContainer.style.cssText = `
          position: absolute !important;
          top: ${top}px !important;
          left: ${left}px !important;
          z-index: 99999 !important;
          display: block !important;
          visibility: visible !important;
          opacity: 1 !important;
        `;
      }
    }
    
    // 初始定位
    positionSelector();
    
    // 添加滚动监听器来更新位置
    const updatePosition = () => positionSelector();
    window.addEventListener('scroll', updatePosition);
    window.addEventListener('resize', updatePosition);
    
    // 存储清理函数
    selectorContainer._cleanup = () => {
      window.removeEventListener('scroll', updatePosition);
      window.removeEventListener('resize', updatePosition);
      document.removeEventListener('click', globalClickHandler, true);
      selectorContainer.remove();
    };
  });
}

// 更新现有选择器位置的函数
function updateSelectorPosition(selectorContainer, pre) {
  console.log('更新选择器位置，选择器:', selectorContainer);
  
  const preRect = pre.getBoundingClientRect();
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
  const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
  
  console.log('代码块位置:', preRect);
  
  if (preRect.width > 0 && preRect.height > 0) {
    const top = preRect.top + scrollTop + 8;
    const left = preRect.right + scrollLeft - 120;
    
    console.log('计算新位置:', { top, left });
    
    selectorContainer.style.position = 'absolute';
    selectorContainer.style.top = `${top}px`;
    selectorContainer.style.left = `${left}px`;
    selectorContainer.style.display = 'block';
    selectorContainer.style.visibility = 'visible';
    selectorContainer.style.opacity = '1';
    selectorContainer.style.zIndex = '99999';
    
    console.log('选择器样式更新后:', selectorContainer.style.cssText);
  } else {
    console.log('代码块尺寸无效，跳过位置更新');
  }
}

// 清除所有悬浮选择器的函数（用于组件卸载等场景）
function clearFloatingSelectors() {
  const existingSelectors = document.querySelectorAll('.floating-lang-selector-container, .floating-lang-selector');
  console.log('清理悬浮选择器，找到数量:', existingSelectors.length);
  existingSelectors.forEach(selector => {
    console.log('移除选择器:', selector);
    if (selector._cleanup) {
      selector._cleanup();
    } else {
      selector.remove();
    }
  });
}

// 检测代码块当前语言
function detectCodeBlockLanguage(pre) {
  console.log('检测代码块语言，元素:', pre);
  console.log('data-language:', pre.dataset.language);
  console.log('className:', pre.className);
  
  // 方法1：从 data-language 属性检测
  if (pre.dataset.language && pre.dataset.language !== 'undefined') {
    console.log('从data-language检测到语言:', pre.dataset.language);
    return pre.dataset.language;
  }
  
  // 方法2：从 class 属性检测 language- 前缀
  const classes = pre.className.split(' ');
  for (const cls of classes) {
    if (cls.startsWith('language-')) {
      const lang = cls.replace('language-', '');
      console.log('从class检测到语言:', lang);
      return lang;
    }
  }
  
  // 方法3：从 code 子元素的 class 属性检测
  const codeElement = pre.querySelector('code');
  if (codeElement) {
    console.log('检查code元素的class:', codeElement.className);
    
    const codeClasses = codeElement.className.split(' ');
    for (const cls of codeClasses) {
      // 检测 language- 前缀
      if (cls.startsWith('language-')) {
        const lang = cls.replace('language-', '');
        console.log('从code的class检测到语言:', lang);
        return lang;
      }
      
      // 检测 hljs- 前缀（highlight.js格式）
      if (cls.startsWith('hljs-') && cls !== 'hljs-code' && cls !== 'hljs-keyword') {
        const lang = cls.replace('hljs-', '');
        // 确保是语言而不是语法高亮类
        if (supportedLanguages.some(l => l.value === lang)) {
          console.log('从hljs class检测到语言:', lang);
          return lang;
        }
      }
    }
  }
  
  // 方法4：使用 highlight.js 内置自动检测
  if (codeElement) {
    const content = codeElement.textContent.trim();
    
    if (content.length > 10) { // 内容足够长才进行检测
      try {
        console.log('使用highlight.js自动检测，内容片段:', content.substring(0, 100));
        
        // 使用highlight.js的highlightAuto进行语言检测
        const result = lowlight.highlightAuto(content);
        console.log('highlight.js检测结果:', result);
        
        if (result && result.data && result.data.language) {
          const detectedLang = result.data.language;
          const relevance = result.data.relevance || 0;
          
          console.log(`highlight.js检测到语言: ${detectedLang}, 相关性: ${relevance}`);
          
          // 检查检测到的语言是否在我们支持的列表中
          const supportedLang = supportedLanguages.find(l => l.value === detectedLang);
          if (supportedLang && relevance > 5) { // 相关性阈值，避免低置信度的检测
            console.log(`智能检测为 ${supportedLang.label} (置信度: ${relevance})`);
            return detectedLang;
          } else if (supportedLang) {
            console.log(`检测到 ${detectedLang} 但置信度较低 (${relevance})，继续其他检测`);
          } else {
            console.log(`检测到 ${detectedLang} 但不在支持列表中`);
          }
        }
      } catch (error) {
        console.log('highlight.js自动检测失败:', error);
      }
    }
  }
  
  console.log('未能检测到语言，返回auto');
  return 'auto';
}



onBeforeUnmount(() => {
  // 清理悬浮选择器
  clearFloatingSelectors();
  
  // 清理编辑器
  if(editor){ 
    editor.destroy(); 
    editor=null; 
  }
});
</script>
<style scoped>
/* ====== 现代化编辑器样式 ====== */
.modern-editor {
  border: 1px solid rgb(229 231 235);
  border-radius: 0.75rem;
  background: white;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
  overflow: hidden;
}

/* 工具栏样式 */
.editor-toolbar {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, rgb(248 250 252) 0%, rgb(241 245 249) 100%);
  border-bottom: 1px solid rgb(229 231 235);
  gap: 0.75rem;
  flex-wrap: wrap;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.toolbar-divider {
  width: 1px;
  height: 1.5rem;
  background: rgb(209 213 219);
  margin: 0 0.5rem;
}

.toolbar-spacer {
  flex: 1;
}

.toolbar-btn {
  border-radius: 0.375rem !important;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgb(0 0 0 / 0.1);
}

/* 统计信息样式 */
.word-count,
.reading-time {
  font-size: 0.75rem;
  color: rgb(107 114 128);
  padding: 0.25rem 0.5rem;
  background: rgb(243 244 246);
  border-radius: 0.375rem;
  font-weight: 500;
  margin-left: 0.5rem;
}

.count-number,
.time-number {
  font-weight: 700;
  color: rgb(59 130 246);
}

/* 编辑器容器 */
.editor-container {
  position: relative;
  min-height: 360px;
}

.editor-content {
  min-height: 360px;
  padding: 1.5rem;
  outline: none;
  line-height: 1.7;
  font-size: 1rem;
  color: rgb(17 24 39);
  background: white;
  border: none;
  resize: none;
  word-wrap: break-word;
}

.editor-content :deep(.ProseMirror) {
  min-height: 360px;
  outline: none;
}

.editor-content :deep(.ProseMirror):focus {
  outline: none;
}

.editor-content :deep(p) {
  margin: 0 0 1rem;
  min-height: 1.5rem;
  line-height: 1.7;
}

.editor-content :deep(h2) {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 1.5rem 0 1rem;
  color: rgb(17 24 39);
  line-height: 1.3;
}

.editor-content :deep(h3) {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 1.25rem 0 0.75rem;
  color: rgb(31 41 55);
  line-height: 1.4;
}

.editor-content :deep(ul),
.editor-content :deep(ol) {
  margin: 1rem 0;
  padding-left: 1.5rem;
}

.editor-content :deep(li) {
  margin: 0.5rem 0;
  line-height: 1.6;
}

/* 现代化语法高亮代码块样式 - 强制应用 */
.editor-content :deep(pre) {
  background: #0d1117 !important;
  color: #f0f6fc !important;
  padding: 1.25rem !important;
  border-radius: 0.75rem !important;
  margin: 1.5rem 0 !important;
  overflow-x: auto !important;
  font-family: 'Fira Code', 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace !important;
  font-size: 0.875rem !important;
  line-height: 1.6 !important;
  border: 1px solid #30363d !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
  position: relative !important;
}

/* Lowlight 语法高亮样式 */
.editor-content :deep(.hljs) {
  background: transparent !important;
  color: #f0f6fc !important;
}

/* 语法高亮颜色配置 - GitHub Dark 主题 */
.editor-content :deep(.hljs-comment),
.editor-content :deep(.hljs-quote) {
  color: #8b949e !important;
  font-style: italic;
}

.editor-content :deep(.hljs-keyword),
.editor-content :deep(.hljs-selector-tag),
.editor-content :deep(.hljs-literal),
.editor-content :deep(.hljs-type) {
  color: #ff7b72 !important;
}

.editor-content :deep(.hljs-string),
.editor-content :deep(.hljs-regexp) {
  color: #a5d6ff !important;
}

.editor-content :deep(.hljs-subst),
.editor-content :deep(.hljs-symbol) {
  color: #f0f6fc !important;
}

.editor-content :deep(.hljs-class),
.editor-content :deep(.hljs-function),
.editor-content :deep(.hljs-title) {
  color: #d2a8ff !important;
}

.editor-content :deep(.hljs-params),
.editor-content :deep(.hljs-built_in) {
  color: #ffa657 !important;
}

.editor-content :deep(.hljs-number),
.editor-content :deep(.hljs-literal) {
  color: #79c0ff !important;
}

.editor-content :deep(.hljs-variable),
.editor-content :deep(.hljs-template-variable) {
  color: #ffa657 !important;
}

.editor-content :deep(.hljs-attribute) {
  color: #79c0ff !important;
}

/* 优化后的行内代码样式 */
.editor-content :deep(code) {
  background: #f6f8fa;
  color: #d73a49;
  padding: 0.1875rem 0.375rem;
  border-radius: 0.375rem;
  font-family: 'Fira Code', 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 0.85em;
  font-weight: 500;
  border: 1px solid #e1e4e8;
}

/* 代码块内的 code 元素 - 确保清晰显示 */
.editor-content :deep(pre code) {
  background: transparent !important;
  color: #f0f6fc !important;
  padding: 0 !important;
  border: none !important;
  border-radius: 0 !important;
  font-weight: 400 !important;
  font-size: 0.875rem !important;
  line-height: 1.6 !important;
}

/* 特殊处理 TipTap 生成的代码块 - 覆盖所有可能的选择器 */
.editor-content :deep(.ProseMirror pre),
.editor-content :deep(.ProseMirror pre[data-language]),
.editor-content :deep(.ProseMirror .hljs),
.editor-content :deep(.ProseMirror pre.hljs) {
  background: #0d1117 !important;
  color: #f0f6fc !important;
  border: 1px solid #30363d !important;
  padding: 1.25rem !important;
  border-radius: 0.75rem !important;
  font-family: 'Fira Code', 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace !important;
}

.editor-content :deep(.ProseMirror pre code),
.editor-content :deep(.ProseMirror pre[data-language] code),
.editor-content :deep(.ProseMirror .hljs code),
.editor-content :deep(.ProseMirror pre.hljs code) {
  background: transparent !important;
  color: #f0f6fc !important;
  font-size: 0.875rem !important;
  line-height: 1.6 !important;
  padding: 0 !important;
  border: none !important;
  border-radius: 0 !important;
}

/* 覆盖可能的 Element Plus 或其他样式 */
.modern-editor .editor-content :deep(pre),
.modern-editor .editor-content :deep(.ProseMirror pre) {
  background: #0d1117 !important;
  color: #f0f6fc !important;
  border: 1px solid #30363d !important;
}

.modern-editor .editor-content :deep(pre code),
.modern-editor .editor-content :deep(.ProseMirror pre code) {
  background: transparent !important;
  color: #f0f6fc !important;
}

.editor-content :deep(blockquote) {
  border-left: 4px solid rgb(59 130 246);
  padding-left: 1rem;
  margin: 1rem 0;
  color: rgb(107 114 128);
  font-style: italic;
}

.editor-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
  margin: 1rem 0;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

/* 占位符样式 */
.editor-placeholder {
  position: absolute;
  top: 1.5rem;
  left: 1.5rem;
  color: rgb(156 163 175);
  font-size: 1rem;
  pointer-events: none;
  user-select: none;
}

/* 状态栏样式 */
.editor-statusbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: rgb(249 250 251);
  border-top: 1px solid rgb(229 231 235);
  font-size: 0.75rem;
}

.statusbar-left {
  color: rgb(107 114 128);
}

.statusbar-right {
  display: flex;
  align-items: center;
}

.status-text {
  font-weight: 500;
}

.preview-btn {
  font-size: 0.75rem !important;
  padding: 0.375rem 0.75rem !important;
  border-radius: 0.375rem !important;
}

.preview-btn .el-icon {
  margin-right: 0.25rem;
  font-size: 0.875rem;
}

/* 隐藏的文件输入 */
.hidden {
  display: none;
}

/* 链接对话框样式覆盖 */
:deep(.el-dialog) {
  border-radius: 0.75rem;
}

:deep(.el-dialog__header) {
  background: linear-gradient(135deg, rgb(248 250 252) 0%, rgb(241 245 249) 100%);
  border-bottom: 1px solid rgb(229 231 235);
  border-radius: 0.75rem 0.75rem 0 0;
}

:deep(.el-dialog__body) {
  padding: 1.5rem;
}

:deep(.el-dialog__footer) {
  padding: 1rem 1.5rem;
  background: rgb(249 250 251);
  border-top: 1px solid rgb(229 231 235);
  border-radius: 0 0 0.75rem 0.75rem;
}

/* Element Plus 按钮样式覆盖 */
:deep(.el-button) {
  font-weight: 500;
  transition: all 0.2s ease;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, rgb(59 130 246), rgb(37 99 235));
  border: none;
}

:deep(.el-button--primary):hover {
  background: linear-gradient(135deg, rgb(37 99 235), rgb(29 78 216));
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgb(59 130 246 / 0.3);
}

/* 主题切换器样式 */
.theme-dropdown {
  margin-left: 0.5rem;
}

:deep(.theme-option) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 4px 0;
}

:deep(.theme-name) {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

:deep(.theme-preview) {
  width: 24px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  flex-shrink: 0;
  margin-left: 8px;
}

:deep(.el-dropdown-menu__item.is-active) {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

:deep(.el-dropdown-menu__item.is-active .theme-name) {
  color: #2563eb;
}

:deep(.el-dropdown-menu) {
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
}

:deep(.el-dropdown-menu__item) {
  padding: 8px 16px;
  font-size: 0.875rem;
  border-radius: 4px;
  margin: 2px 4px;
}

:deep(.el-dropdown-menu__item:hover) {
  background: #f3f4f6;
}

/* 工具提示样式 */
:deep(.el-tooltip__popper) {
  font-size: 0.75rem;
  border-radius: 0.375rem;
}

/* 悬浮语言选择器容器样式 */
.floating-lang-selector-container {
  position: absolute !important;
  z-index: 9999 !important;
  font-size: 12px !important;
  font-family: var(--el-font-family) !important;
}

/* Element Plus 风格的选择器 */
.el-select-styled {
  position: relative;
  display: inline-block;
}

.el-select__wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  width: 100px;
  min-height: 28px;
  background-color: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  box-shadow: 0 0 0 1px var(--el-input-border-color, var(--el-border-color)) inset;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  padding: 1px 8px 1px 8px;
}

.el-select__wrapper:hover {
  border-color: var(--el-border-color-hover);
}

.el-select__wrapper.is-focused {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}

.el-select__selection {
  display: flex;
  align-items: center;
  flex-grow: 1;
  gap: 4px;
  min-width: 0;
}

.el-select__selected-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-text-color-primary);
  font-size: 12px;
}

.el-select__suffix {
  display: flex;
  align-items: center;
  color: var(--el-text-color-placeholder);
  transition: transform 0.2s;
}

.el-select__dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #ffffff !important;
  border: 1px solid #dcdfe6 !important;
  border-radius: 6px !important;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12) !important;
  margin-top: 4px;
  z-index: 99999 !important;
  max-height: 200px;
  overflow: hidden;
  display: none;
  backdrop-filter: blur(8px);
}

.el-select-dropdown__list {
  padding: 4px 0;
}

.el-select-dropdown__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  font-size: 12px;
  color: var(--el-text-color-regular);
  cursor: pointer;
  transition: background-color 0.2s;
}

.el-select-dropdown__item:hover {
  background-color: var(--el-fill-color-light);
}

.el-select-dropdown__item.is-selected {
  color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

.el-select__check-icon {
  color: var(--el-color-primary);
  font-size: 12px;
}

/* 深色主题支持 */
@media (prefers-color-scheme: dark) {
  .floating-lang-selector-container .el-select__wrapper {
    background-color: var(--el-bg-color);
    border-color: var(--el-border-color);
  }
  
  .floating-lang-selector-container .el-select__dropdown {
    background: #2c2c2c !important;
    border: 1px solid #4c4c4c !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.25) !important;
  }
  
  .floating-lang-selector-container .el-select-dropdown__item {
    color: #e6e6e6 !important;
  }
  
  .floating-lang-selector-container .el-select-dropdown__item:hover {
    background-color: #3c3c3c !important;
  }
  
  .floating-lang-selector-container .el-select-dropdown__item.is-selected {
    background-color: #264f78 !important;
    color: #9cdcfe !important;
  }
}

/* 代码块相对定位以便语言选择器绝对定位 */
:deep(pre) {
  position: relative !important;
}

:deep(pre.hljs) {
  position: relative !important;
}

:deep(pre.code-block-with-lang) {
  position: relative !important;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .editor-toolbar {
    padding: 0.5rem;
    gap: 0.25rem;
  }
  
  .toolbar-group {
    gap: 0.125rem;
  }
  
  .toolbar-divider {
    margin: 0 0.25rem;
  }
  
  .word-count,
  .reading-time {
    font-size: 0.625rem;
    padding: 0.125rem 0.375rem;
    margin-left: 0.25rem;
  }
  
  .editor-content {
    padding: 1rem;
    font-size: 0.875rem;
  }
  
  .editor-placeholder {
    top: 1rem;
    left: 1rem;
    font-size: 0.875rem;
  }
  
  .editor-statusbar {
    padding: 0.5rem;
    font-size: 0.625rem;
  }
  
  .preview-btn {
    font-size: 0.625rem !important;
    padding: 0.25rem 0.5rem !important;
  }
}
</style>
