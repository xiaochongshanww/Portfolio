<template>
  <div class="focal-cropper" v-if="imageSrc">
    <div class="canvas-wrap" ref="wrapRef" @click="setFocal($event)">
      <img :src="imageSrc" ref="imgRef" @load="onLoad" class="preview" />
      <div v-if="focalSet" class="focal-dot" :style="dotStyle"></div>
    </div>
    <div class="controls">
      <label>裁剪比例:
        <select v-model="aspect">
          <option value="16:9">16:9</option>
          <option value="4:3">4:3</option>
          <option value="1:1">1:1</option>
          <option value="3:4">3:4</option>
        </select>
      </label>
      <button type="button" @click="emitResult">应用</button>
    </div>
  </div>
  <div v-else class="empty">未选择图片</div>
</template>
<script setup>
import { ref, computed, watch } from 'vue';
const props = defineProps({ modelValue:String });
const emits = defineEmits(['update:modelValue','focal-change','cropped']);
const imageSrc = computed(()=>props.modelValue);
const imgRef = ref();
const wrapRef = ref();
const focal = ref({ x:0.5, y:0.5 });
const focalSet = ref(false);
const aspect = ref('16:9');
function onLoad(){ /* 可计算 natural 尺寸 */ }
function setFocal(e){
  const rect = wrapRef.value.getBoundingClientRect();
  focal.value = { x:(e.clientX-rect.left)/rect.width, y:(e.clientY-rect.top)/rect.height };
  focalSet.value = true;
  emits('focal-change', focal.value);
}
const dotStyle = computed(()=>({ left:(focal.value.x*100)+'%', top:(focal.value.y*100)+'%' }));
function emitResult(){
  // 简化：只返回焦点；裁剪操作交给服务端或 CSS object-position
  emits('cropped', { focal_x:focal.value.x, focal_y:focal.value.y, aspect:aspect.value });
}
watch(()=>props.modelValue, ()=>{ focalSet.value=false; });
</script>
<style scoped>
.focal-cropper { border:1px solid #ddd; padding:8px; display:flex; flex-direction:column; gap:8px; max-width:480px; }
.canvas-wrap { position:relative; width:100%; overflow:hidden; cursor:crosshair; }
.preview { width:100%; display:block; }
.focal-dot { position:absolute; width:14px; height:14px; background:#ff5252; border:2px solid #fff; border-radius:50%; transform:translate(-50%, -50%); box-shadow:0 0 4px rgba(0,0,0,.4); pointer-events:none; }
.controls { display:flex; gap:12px; align-items:center; }
.empty { padding:1rem; color:#888; }
</style>
