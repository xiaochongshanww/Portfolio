<template>
  <div class="rich-md-editor">
    <textarea ref="ta" />
  </div>
</template>
<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import EasyMDE from 'easymde';
import 'easymde/dist/easymde.min.css';
import api from '../apiClient';

const props = defineProps({
  modelValue: { type: String, default: '' }
});
const emit = defineEmits(['update:modelValue','image-uploaded']);
const ta = ref(null);
let mde = null;

async function uploadImage(file){
  const fd = new FormData(); fd.append('file', file);
  try {
    const r = await api.post('/api/v1/uploads/image', fd, { headers:{ 'Content-Type':'multipart/form-data' }});
    const meta = r.data?.data;
    if(meta){
      const url = meta.url;
      let insert;
      if(meta.srcset || meta.lqip){
        // 使用自适应图片结构（降级为普通 img）
        const attrSrcset = meta.srcset ? ` srcset="${meta.srcset}"` : '';
        const placeholder = meta.lqip ? ` style=\"background: #f0f0f0 url('${meta.lqip}') center/cover no-repeat;\"` : '';
        insert = `\n<picture><img src="${url}"${attrSrcset} sizes="(max-width: 800px) 100vw, 800px" alt="image" loading="lazy"${placeholder}></picture>\n`;
      } else {
        insert = `![image](${url})`;
      }
      const pos = mde.codemirror.getCursor();
      mde.codemirror.replaceRange(insert, pos);
      emit('update:modelValue', mde.value());
      emit('image-uploaded', meta);
    }
  } catch(e){
    console.error('image upload failed', e);
  }
}

function handlePaste(cm, e){
  const items = e.clipboardData?.items; if(!items) return;
  for(const it of items){ if(it.kind==='file'){ const f = it.getAsFile(); if(f && f.type.startsWith('image/')){ uploadImage(f); break; } } }
}
function handleDrop(cm, e){
  const files = e.dataTransfer?.files; if(!files) return;
  for(const f of files){ if(f.type.startsWith('image/')){ uploadImage(f); break; } }
}

onMounted(()=>{
  const videoBtn = {
    name: 'video',
    action: (editor)=>{
  const url = window.prompt('视频链接 (YouTube / Bilibili / Vimeo)');
      if(!url) return;
      const insert = `\n:::video ${url}:::\n`;
      const cm = editor.codemirror; const pos = cm.getCursor();
      cm.replaceRange(insert, pos); emit('update:modelValue', editor.value());
    },
    className: 'fa fa-film',
    title: '插入视频'
  };
  const gistBtn = {
    name: 'gist',
    action: (editor)=>{
      const url = window.prompt('GitHub Gist 原始地址 或 gist 链接');
      if(!url) return;
      const insert = `\n:::gist ${url}:::\n`;
      const cm = editor.codemirror; const pos = cm.getCursor();
      cm.replaceRange(insert, pos); emit('update:modelValue', editor.value());
    },
    className: 'fa fa-code',
    title: '插入 Gist'
  };
  mde = new EasyMDE({
    element: ta.value,
    autofocus: false,
    spellChecker: false,
    status: false,
    initialValue: props.modelValue,
    renderingConfig: { singleLineBreaks: false },
    toolbar: ['bold','italic','strikethrough','heading','|','quote','unordered-list','ordered-list','table','|','link','image',videoBtn,gistBtn,'code','|','preview','side-by-side','fullscreen','guide']
  });
  mde.codemirror.on('change', ()=> emit('update:modelValue', mde.value()));
  mde.codemirror.on('paste', handlePaste);
  mde.codemirror.on('drop', handleDrop);
});

watch(()=>props.modelValue, v=>{ if(mde && mde.value()!==v){ mde.value(v || ''); } });

onBeforeUnmount(()=>{ mde && (mde.toTextArea()); mde=null; });
</script>
<style scoped>
.rich-md-editor :deep(.EasyMDEContainer) { border:1px solid #ccc; border-radius:4px; }
</style>
