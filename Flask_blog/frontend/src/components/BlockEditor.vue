<template>
  <div class="block-editor">
    <div class="toolbar">
      <button type="button" @click="cmd('bold')" :class="{active:isActive('bold')}"><b>B</b></button>
      <button type="button" @click="cmd('italic')" :class="{active:isActive('italic')}"><i>I</i></button>
      <button type="button" @click="toggleHeading(2)" :class="{active:isHeading(2)}">H2</button>
      <button type="button" @click="toggleHeading(3)" :class="{active:isHeading(3)}">H3</button>
      <button type="button" @click="cmd('bullet')">• 列表</button>
      <button type="button" @click="cmd('ordered')">1. 列表</button>
      <button type="button" @click="cmd('codeblock')" :class="{active:isActive('codeBlock')}">代码块</button>
      <button type="button" @click="insertImageDialog">图片</button>
      <button type="button" @click="openVideoDialog">视频</button>
      <button type="button" @click="openGistDialog">Gist</button>
    </div>
  <div ref="editorEl" class="editor-content" tabindex="0" @click="focusEditor" />
    <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleFileChange" />
  </div>
</template>
<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import { Editor } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import Image from '@tiptap/extension-image';
import Turndown from 'turndown';
import { mdToHtml, htmlToMd } from '../utils/editorConversion';
import api from '../apiClient';

const props = defineProps({ modelValue: { type: String, default: '' } });
const emit = defineEmits(['update:modelValue','image-uploaded']);
const editorEl = ref(null);
let editor; // TipTap 实例
const turndownService = new Turndown({ headingStyle: 'atx', codeBlockStyle: 'fenced' });

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
function updateModelFromEditor(){ const html = editor.getHTML(); const md = toMarkdownFromHTML(html); emit('update:modelValue', md); }

onMounted(()=>{
  const initialHTML = mdToHtml(props.modelValue || '');
  editor = new Editor({ element: editorEl.value, content: initialHTML, extensions: [StarterKit, Image], autofocus: false, onUpdate(){ updateModelFromEditor(); } });
  editorEl.value.addEventListener('paste', handlePaste);
  editorEl.value.addEventListener('drop', handleDrop);
});

watch(()=>props.modelValue, (v)=>{ if(!editor) return; const currentMd = toMarkdownFromHTML(editor.getHTML()); if(v !== currentMd){ editor.commands.setContent(mdToHtml(v || ''), false); } });

// 工具栏命令
function cmd(action){ if(!editor) return; const ch = editor.chain().focus(); switch(action){ case 'bold': ch.toggleBold().run(); break; case 'italic': ch.toggleItalic().run(); break; case 'bullet': ch.toggleBulletList().run(); break; case 'ordered': ch.toggleOrderedList().run(); break; case 'codeblock': ch.toggleCodeBlock().run(); break; } updateModelFromEditor(); }
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

function focusEditor(){ if(editor){ editor.commands.focus('end'); } }

onBeforeUnmount(()=>{ if(editor){ editor.destroy(); editor=null; } });
</script>
<style scoped>
.block-editor { border:1px solid #ccc; border-radius:4px; display:flex; flex-direction:column; }
.toolbar { display:flex; gap:6px; flex-wrap:wrap; padding:6px; border-bottom:1px solid #ddd; background:#f9f9f9; }
.toolbar button { background:#fff; border:1px solid #ccc; padding:4px 8px; font-size:12px; border-radius:4px; cursor:pointer; }
.toolbar button.active { background:#1677ff; color:#fff; border-color:#1677ff; }
/* 关键：让编辑区成为可扩展的块级区域，避免仅一行高度的错觉 */
.editor-content {
  min-height: 360px;
  padding: 12px;
  outline: none;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.editor-content :deep(p) { margin: 0 0 8px; min-height: 1.2em; }
.editor-content :deep(.ProseMirror) { min-height: 360px; }
.editor-content:focus { box-shadow: inset 0 0 0 1px #1677ff33; }
.hidden { display:none; }
</style>
