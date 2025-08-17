<template>
  <div class="profile" v-if="loaded">
    <h1>个人资料</h1>
    <form @submit.prevent="save">
      <div><label>昵称</label><input v-model="form.nickname" maxlength="80" /></div>
      <div><label>简介</label><textarea v-model="form.bio" maxlength="2000" rows="4"></textarea></div>
      <div><label>头像 URL</label><input v-model="form.avatar" /></div>
      <div><label>社交链接(JSON)</label><textarea v-model="form.social_links_raw" rows="3" placeholder='{"github":"https://github.com/..."}'></textarea></div>
      <button :disabled="saving">保存</button>
      <span v-if="error" class="err">{{ error }}</span>
      <span v-if="saved" class="ok">已保存</span>
    </form>
  </div>
  <div v-else>加载中...</div>
</template>
<script setup>
import { ref, onMounted } from 'vue';
import { UsersService } from '../generated';
import { useNotify } from '../composables/useNotify';
import { setMeta } from '../composables/useMeta';
const { pushError } = useNotify();
const loaded = ref(false); const saving = ref(false); const saved = ref(false); const error = ref('');
const form = ref({ nickname:'', bio:'', avatar:'', social_links_raw:'' });
async function load(){
  try { const r = await UsersService.getApiV1UsersMe(); const d = r.data?.data || r.data || r; form.value.nickname=d.nickname||''; form.value.bio=d.bio||''; form.value.avatar=d.avatar||''; if(d.social_links) form.value.social_links_raw=JSON.stringify(d.social_links, null,2); }catch(e){ pushError('加载失败'); } finally { loaded.value=true; }
}
async function save(){
  saving.value=true; error.value=''; saved.value=false;
  try {
    let socialLinks;
    if(form.value.social_links_raw.trim()){
      try { socialLinks = JSON.parse(form.value.social_links_raw); } catch(e){ error.value='社交链接 JSON 无效'; saving.value=false; return; }
    }
    const payload = { nickname: form.value.nickname||undefined, bio: form.value.bio||undefined, avatar: form.value.avatar||undefined, social_links: socialLinks };
    await UsersService.patchApiV1UsersMe(payload);
    saved.value=true;
  }catch(e){ error.value='保存失败'; } finally { saving.value=false; }
}
onMounted(()=>{ setMeta({ title:'个人资料', description:'编辑个人资料' }); load(); });
</script>
<style scoped>
.profile { max-width:560px; }
form div { margin-bottom:10px; display:flex; flex-direction:column; }
label { font-size:12px; color:#555; margin-bottom:2px; }
input, textarea { padding:6px 8px; font-size:14px; }
button { padding:6px 14px; cursor:pointer; }
.err { color:#d00; margin-left:12px; }
ok { color:#070; }
</style>
