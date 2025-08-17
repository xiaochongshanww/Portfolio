<template>
  <div>
    <h1>新建文章</h1>
    <div class="form">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="标题" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="SEO 标题">
              <el-input v-model="form.seo_title" placeholder="SEO 标题" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Meta 描述">
              <el-input v-model="form.seo_desc" placeholder="Meta 描述" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="自定义 Slug (可选)">
              <el-input v-model="form.slug" placeholder="自定义 Slug (可选)" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="特色图 URL (必填, ≥800x450)">
              <el-input v-model="form.featured_image" placeholder="https://..." />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="文章摘要 (可选)">
          <el-input v-model="form.summary" type="textarea" :rows="3" placeholder="文章摘要" />
        </el-form-item>
        <div class="toolbar">
          <ImageUploader @uploaded="onFeaturedCandidate" />
          <span v-if="form.featured_image" class="mini-thumb">封面预览: <img :src="form.featured_image" alt="thumb" /></span>
        </div>
        <ImageFocalCropper v-if="form.featured_image" v-model="form.featured_image" @focal-change="onFocal" />
        <BlockEditor v-model="form.content_md" @image-uploaded="insertImage" />
        <el-form-item label="标签(逗号分隔)">
          <el-input v-model="form.tags_raw" placeholder="如：vue,flask,python" />
        </el-form-item>
        <div class="schedule-row">
          <el-switch v-model="form.enable_schedule" active-text="定时发布" />
          <el-date-picker v-if="form.enable_schedule" v-model="form.scheduled_at" type="datetime" placeholder="选择时间" />
        </div>
        <div>
          <el-button type="primary" :loading="loading" @click="submit">提交</el-button>
        </div>
        <el-alert v-if="error" :title="error" type="error" show-icon class="mt-12" />
      </el-form>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue';
import { API } from '../api';
import api from '../apiClient';
import BlockEditor from '../components/BlockEditor.vue';
import { ERROR_CODE_MAP } from '../governance/errorCodes.generated';
import { useRouter } from 'vue-router';
import ImageUploader from '../components/ImageUploader.vue';
import ImageFocalCropper from '../components/ImageFocalCropper.vue';
import { setMeta } from '../composables/useMeta';
const router = useRouter();
const form = ref({ title:'', content_md:'', tags_raw:'', seo_title:'', seo_desc:'', slug:'', summary:'', featured_image:'', featured_focal_x:null, featured_focal_y:null, enable_schedule:false, scheduled_at:'' });
const loading = ref(false);
const error = ref('');
function mapErr(code, fallback){ return ERROR_CODE_MAP.get(code) || fallback; }
function insertImage(meta){
  const tag = `![${meta.width || ''}x${meta.height || ''}](${meta.url})`;
  form.value.content_md = (form.value.content_md || '') + (form.value.content_md ? '\n' : '') + tag + '\n';
}
function onFeaturedCandidate(meta){
  // 若尚未设置封面图，首次上传默认填入 featured_image
  if(!form.value.featured_image && meta?.url){ form.value.featured_image = meta.url; }
}
function onFocal(f){ form.value.featured_focal_x = f.x; form.value.featured_focal_y = f.y; }
async function checkFeaturedDims(url){
  return new Promise(resolve=>{
    if(!url) return resolve({ok:false, reason:'缺少特色图'});
    const img = new Image();
    img.onload = ()=>{
      const w = img.naturalWidth, h = img.naturalHeight; const ratio = w/h;
      if(w>=800 && h>=450 && ratio >= (16/9)*0.9) resolve({ok:true}); else resolve({ok:false, reason:`当前 ${w}x${h}`});
    };
    img.onerror = ()=>resolve({ok:false, reason:'加载失败'});
    img.src = url;
  });
}
async function submit(){
  loading.value=true; error.value='';
  try {
    // 前端校验特色图
    const imgCheck = await checkFeaturedDims(form.value.featured_image);
    if(!imgCheck.ok){ error.value = '特色图不符合最小尺寸或比例要求 ('+ (imgCheck.reason||'') +')'; loading.value=false; return; }
    const tags = form.value.tags_raw.split(',').map(s=>s.trim()).filter(Boolean);
  const payload = { title: form.value.title, content_md: form.value.content_md, tags };
  if(form.value.slug) payload.slug = form.value.slug.trim();
  if(form.value.seo_title) payload.seo_title = form.value.seo_title;
  if(form.value.seo_desc) payload.seo_desc = form.value.seo_desc;
  if(form.value.summary) payload.summary = form.value.summary;
  if(form.value.featured_image) payload.featured_image = form.value.featured_image;
  if(form.value.featured_focal_x!=null && form.value.featured_focal_y!=null){ payload.featured_focal_x=form.value.featured_focal_x; payload.featured_focal_y=form.value.featured_focal_y; }
  if(form.value.enable_schedule && form.value.scheduled_at) payload.scheduled_at = new Date(form.value.scheduled_at).toISOString();
  const resp = await API.ArticlesService.postApiV1Articles(payload);
    const data = resp.data?.data || resp.data;
    const slug = data.slug || data.id;
    router.push('/article/' + slug);
  } catch(e){
    const code = e.body?.code || e.response?.data?.code;
    error.value = mapErr(code, '提交失败');
  } finally { loading.value=false; }
}
onMounted(()=>{
  setMeta({ title: '撰写新文章', description: '创作中心 - 新建文章' });
});
</script>
<style scoped>
.form { display:flex; flex-direction:column; gap:12px; max-width:720px; }
.editor { min-height:240px; font-family:monospace; }
.toolbar { display:flex; gap:12px; }
.two-cols { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.summary { min-height:80px; }
.mini-thumb img { max-height:40px; vertical-align:middle; }
.schedule-row { display:flex; gap:12px; align-items:center; }
.mt-12 { margin-top: 12px; }
</style>
