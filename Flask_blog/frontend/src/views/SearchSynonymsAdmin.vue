<template>
  <div class="synonyms-admin">
    <h1>搜索同义词管理</h1>
    <form @submit.prevent="add" class="form">
      <input v-model="term" placeholder="主词" required />
      <input v-model="synonymsRaw" placeholder="同义词(逗号)" required />
      <button :disabled="loading">添加/更新</button>
    </form>
    <p v-if="error" class="err">{{ error }}</p>
    <table v-if="list.length" class="table">
      <thead><tr><th>主词</th><th>同义词</th><th></th></tr></thead>
      <tbody>
        <tr v-for="row in list" :key="row.term">
          <td>{{ row.term }}</td>
          <td>{{ row.synonyms.join(', ') }}</td>
          <td><button @click="del(row.term)" :disabled="loading">删除</button></td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">暂无同义词</p>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue';
import api from '../apiClient';
import { useNotify } from '../composables/useNotify';
import { setMeta } from '../composables/useMeta';
const { pushSuccess, pushError } = useNotify();
const term = ref('');
const synonymsRaw = ref('');
const list = ref([]);
const loading = ref(false);
const error = ref('');

async function load(){
  try {
    const r = await api.get('/api/v1/search/synonyms/');
    list.value = r.data?.data || [];
  } catch(e){ pushError('加载失败'); }
}
async function add(){
  loading.value=true; error.value='';
  try {
    const syns = synonymsRaw.value.split(',').map(s=>s.trim()).filter(Boolean);
    const r = await api.post('/api/v1/search/synonyms/', { term: term.value, synonyms: syns });
    pushSuccess('已更新'); term.value=''; synonymsRaw.value=''; await load();
  } catch(e){ pushError('提交失败'); }
  finally { loading.value=false; }
}
async function del(t){
  if(!confirm('确定删除该同义词组?')) return;
  loading.value=true; error.value='';
  try { await api.delete('/api/v1/search/synonyms/' + encodeURIComponent(t)); pushSuccess('已删除'); await load(); }
  catch(e){ pushError('删除失败'); }
  finally { loading.value=false; }
}
onMounted(()=>{ setMeta({ title:'同义词管理' }); load(); });
</script>
<style scoped>
.synonyms-admin { max-width:720px; }
.form { display:flex; gap:8px; margin-bottom:16px; }
.form input { flex:1; }
.table { width:100%; border-collapse:collapse; }
.table th, .table td { border:1px solid #ddd; padding:6px 8px; font-size:14px; }
.err { color:#d33; }
.empty { color:#777; padding:1rem 0; }
</style>
