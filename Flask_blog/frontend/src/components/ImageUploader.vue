<template>
  <div class="uploader">
    <input ref="input" type="file" accept="image/*" @change="onFile" hidden />
    <button type="button" @click="select" :disabled="uploading">{{ uploading? '上传中...' : '上传图片' }}</button>
    <span v-if="error" class="err">{{ error }}</span>
  </div>
</template>
<script setup>
import { ref } from 'vue';
import api from '../apiClient';

const emit = defineEmits(['uploaded']);
const input = ref(null);
const uploading = ref(false);
const error = ref('');

function select(){ input.value && input.value.click(); }
async function onFile(e){
  const f = e.target.files && e.target.files[0];
  if(!f) return;
  error.value='';
  const fd = new FormData();
  fd.append('file', f);
  uploading.value = true;
  try {
    const resp = await api.post('/api/v1/uploads/image', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    const data = resp.data?.data;
    if(data){
      emit('uploaded', data);
    }
  } catch(e){
    error.value = '上传失败';
  } finally { uploading.value=false; input.value && (input.value.value=''); }
}
</script>
<style scoped>
.uploader { display:inline-flex; gap:8px; align-items:center; }
button { padding:4px 10px; font-size:14px; }
.err { color:#d33; font-size:12px; }
</style>
