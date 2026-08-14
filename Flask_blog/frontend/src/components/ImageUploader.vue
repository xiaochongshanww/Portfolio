<template>
  <div class="uploader">
    <input ref="input" type="file" accept="image/*" hidden @change="onFile">
    <button type="button" :disabled="uploading" @click="select">{{ uploading? '上传中...' : '上传图片' }}</button>
    <span v-if="error" class="err">{{ error }}</span>
  </div>
</template>
<script setup>
import { ref } from 'vue';
import api from '../apiClient';

const emit = defineEmits(['uploaded']);
/** @type {import('vue').Ref<HTMLInputElement | null>} */
const input = ref(null);
const uploading = ref(false);
const error = ref('');

function select(){ if(input.value){ input.value.click(); } }
/** @param {Event} e */
async function onFile(e){
  const target = /** @type {HTMLInputElement} */ (e.target);
  const f = target.files && target.files[0];
  if(!f) return;
  error.value='';
  const fd = new FormData();
  fd.append('file', f);
  uploading.value = true;
  try {
    const resp = await api.post('/uploads/image', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    const data = resp.data?.data;
    if(data){
      emit('uploaded', data);
    }
  } catch(_e){
    error.value = '上传失败';
  } finally { uploading.value=false; if(input.value){ input.value.value=''; } }
}
</script>
<style scoped>
.uploader { display:inline-flex; gap:8px; align-items:center; }
button { padding:4px 10px; font-size:14px; }
.err { color:#d33; font-size:12px; }
</style>
