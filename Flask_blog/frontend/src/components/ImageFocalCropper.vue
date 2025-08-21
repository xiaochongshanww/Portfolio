<template>
  <div class="focal-cropper-container" v-if="imageSrc">
    <div class="cropper-header">
      <h4 class="cropper-title">
        <el-icon class="title-icon"><Crop /></el-icon>
        图片焦点设置
      </h4>
      <p class="cropper-subtitle">点击图片设置关键焦点位置，用于不同尺寸下的智能裁剪</p>
    </div>

    <div class="cropper-content">
      <div class="image-container">
        <div class="canvas-wrap" ref="wrapRef" @click="setFocal($event)">
          <img :src="imageSrc" ref="imgRef" @load="onLoad" class="preview-image" />
          <div v-if="focalSet" class="focal-dot" :style="dotStyle">
            <div class="focal-pulse"></div>
          </div>
          <div class="overlay-grid">
            <div class="grid-line grid-line-v" style="left: 33.33%"></div>
            <div class="grid-line grid-line-v" style="left: 66.67%"></div>
            <div class="grid-line grid-line-h" style="top: 33.33%"></div>
            <div class="grid-line grid-line-h" style="top: 66.67%"></div>
          </div>
        </div>
      </div>

      <div class="controls-section">
        <el-form label-position="top" class="cropper-form">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="裁剪比例">
                <el-select v-model="aspect" size="large" style="width: 100%">
                  <el-option value="16:9" label="16:9 (宽屏)">
                    <span class="option-text">16:9</span>
                    <span class="option-desc">宽屏横幅</span>
                  </el-option>
                  <el-option value="4:3" label="4:3 (传统)">
                    <span class="option-text">4:3</span>
                    <span class="option-desc">传统比例</span>
                  </el-option>
                  <el-option value="1:1" label="1:1 (方形)">
                    <span class="option-text">1:1</span>
                    <span class="option-desc">正方形</span>
                  </el-option>
                  <el-option value="3:4" label="3:4 (竖屏)">
                    <span class="option-text">3:4</span>
                    <span class="option-desc">竖屏比例</span>
                  </el-option>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="焦点坐标">
                <div class="focal-coords">
                  <span class="coord-label">X: {{ (focal.x * 100).toFixed(1) }}%</span>
                  <span class="coord-label">Y: {{ (focal.y * 100).toFixed(1) }}%</span>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <div class="action-buttons">
          <el-button 
            type="primary" 
            size="large"
            @click="emitResult"
            :disabled="!focalSet"
          >
            <el-icon><Check /></el-icon>
            应用设置
          </el-button>
          <el-button 
            size="large"
            @click="resetFocal"
          >
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
        </div>
      </div>
    </div>

    <div class="help-section">
      <el-alert
        title="使用提示"
        type="info"
        :closable="false"
      >
        <template #default>
          <ul class="help-list">
            <li>点击图片设置焦点位置，系统会在不同显示尺寸下保持焦点区域可见</li>
            <li>网格线帮助您使用三分法则构图，焦点通常设置在交叉点附近效果更佳</li>
            <li>不同的裁剪比例适用于不同场景：16:9适合横幅，1:1适合社交媒体</li>
          </ul>
        </template>
      </el-alert>
    </div>
  </div>
  <div v-else class="empty-state">
    <el-icon class="empty-icon"><Picture /></el-icon>
    <p class="empty-text">请先上传或选择图片</p>
  </div>
</template>
<script setup>
import { ref, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { 
  Crop, Check, RefreshLeft, Picture
} from '@element-plus/icons-vue';

const props = defineProps({ 
  modelValue: {
    type: String,
    default: ''
  }
});

const emits = defineEmits(['update:modelValue', 'focal-change', 'cropped']);

// 响应式数据
const imageSrc = computed(() => props.modelValue);
const imgRef = ref();
const wrapRef = ref();
const focal = ref({ x: 0.5, y: 0.5 });
const focalSet = ref(false);
const aspect = ref('16:9');

// 计算属性
const dotStyle = computed(() => ({
  left: (focal.value.x * 100) + '%',
  top: (focal.value.y * 100) + '%'
}));

// 方法
function onLoad() {
  // 图片加载完成，可以计算natural尺寸
  console.log('Image loaded');
}

function setFocal(e) {
  if (!wrapRef.value) return;
  
  const rect = wrapRef.value.getBoundingClientRect();
  const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
  
  focal.value = { x, y };
  focalSet.value = true;
  
  // 触发变化事件
  emits('focal-change', focal.value);
  
  ElMessage.success(`焦点已设置: (${(x * 100).toFixed(1)}%, ${(y * 100).toFixed(1)}%)`);
}

function resetFocal() {
  focal.value = { x: 0.5, y: 0.5 };
  focalSet.value = false;
  emits('focal-change', focal.value);
  ElMessage.info('焦点已重置到中心位置');
}

function emitResult() {
  if (!focalSet.value) {
    ElMessage.warning('请先点击图片设置焦点位置');
    return;
  }
  
  const result = {
    focal_x: focal.value.x,
    focal_y: focal.value.y,
    aspect: aspect.value
  };
  
  emits('cropped', result);
  ElMessage.success('焦点设置已应用');
}

// 监听器
watch(() => props.modelValue, (newValue) => {
  if (newValue) {
    // 新图片时重置焦点
    focalSet.value = false;
    focal.value = { x: 0.5, y: 0.5 };
  }
});
</script>
<style scoped>
/* 焦点裁剪器容器 */
.focal-cropper-container {
  background: white;
  border-radius: 1rem;
  border: 1px solid rgb(229 231 235);
  overflow: hidden;
  margin-top: 1rem;
}

/* 头部 */
.cropper-header {
  padding: 1.5rem;
  background: linear-gradient(135deg, rgb(248 250 252) 0%, rgb(241 245 249) 100%);
  border-bottom: 1px solid rgb(229 231 235);
}

.cropper-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: rgb(17 24 39);
  margin: 0 0 0.5rem 0;
}

.title-icon {
  color: rgb(59 130 246);
  font-size: 1.25rem;
}

.cropper-subtitle {
  color: rgb(107 114 128);
  font-size: 0.875rem;
  margin: 0;
  line-height: 1.5;
}

/* 内容区域 */
.cropper-content {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 图片容器 */
.image-container {
  display: flex;
  justify-content: center;
}

.canvas-wrap {
  position: relative;
  max-width: 500px;
  width: 100%;
  border-radius: 0.75rem;
  overflow: hidden;
  cursor: crosshair;
  box-shadow: 0 8px 16px rgb(0 0 0 / 0.15);
  transition: all 0.3s ease;
}

.canvas-wrap:hover {
  box-shadow: 0 12px 24px rgb(0 0 0 / 0.2);
  transform: translateY(-2px);
}

.preview-image {
  width: 100%;
  height: auto;
  display: block;
  user-select: none;
}

/* 覆盖网格 */
.overlay-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.canvas-wrap:hover .overlay-grid {
  opacity: 0.6;
}

.grid-line {
  position: absolute;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 0 1px rgba(0, 0, 0, 0.3);
}

.grid-line-v {
  width: 1px;
  height: 100%;
}

.grid-line-h {
  height: 1px;
  width: 100%;
}

/* 焦点标记 */
.focal-dot {
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 10;
  background: rgb(239 68 68);
  border: 3px solid white;
  box-shadow: 
    0 0 0 2px rgb(239 68 68 / 0.3),
    0 4px 12px rgb(0 0 0 / 0.3);
  animation: focusPulse 2s ease-in-out infinite;
}

.focal-pulse {
  position: absolute;
  top: -3px;
  left: -3px;
  right: -3px;
  bottom: -3px;
  border-radius: 50%;
  border: 2px solid rgb(239 68 68);
  animation: pulseRing 2s ease-out infinite;
}

@keyframes focusPulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.1); }
}

@keyframes pulseRing {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

/* 控制区域 */
.controls-section {
  background: rgb(248 250 252);
  border-radius: 0.75rem;
  padding: 1.5rem;
  border: 1px solid rgb(229 231 235);
}

.cropper-form {
  margin-bottom: 1.5rem;
}

/* 选项样式 */
.option-text {
  font-weight: 600;
  color: rgb(17 24 39);
}

.option-desc {
  color: rgb(107 114 128);
  font-size: 0.875rem;
  margin-left: 0.5rem;
}

/* 焦点坐标显示 */
.focal-coords {
  display: flex;
  gap: 1rem;
  padding: 0.75rem;
  background: white;
  border-radius: 0.5rem;
  border: 1px solid rgb(209 213 219);
}

.coord-label {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 0.875rem;
  font-weight: 600;
  color: rgb(59 130 246);
  padding: 0.25rem 0.5rem;
  background: rgb(239 246 255);
  border-radius: 0.25rem;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

/* 帮助区域 */
.help-section {
  padding: 1.5rem;
  background: rgb(254 249 195);
  border-top: 1px solid rgb(229 231 235);
}

.help-list {
  margin: 0;
  padding-left: 1.25rem;
  color: rgb(75 85 99);
  line-height: 1.6;
}

.help-list li {
  margin-bottom: 0.5rem;
}

.help-list li:last-child {
  margin-bottom: 0;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1.5rem;
  background: rgb(248 250 252);
  border-radius: 1rem;
  border: 2px dashed rgb(203 213 225);
  margin-top: 1rem;
}

.empty-icon {
  font-size: 3rem;
  color: rgb(156 163 175);
  margin-bottom: 1rem;
}

.empty-text {
  color: rgb(107 114 128);
  font-size: 1rem;
  margin: 0;
  text-align: center;
}

/* Element Plus 样式覆盖 */
:deep(.el-form-item__label) {
  font-weight: 600;
  color: rgb(17 24 39);
  margin-bottom: 0.5rem;
}

:deep(.el-select .el-input__wrapper) {
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
}

:deep(.el-button) {
  border-radius: 0.5rem;
  font-weight: 500;
  padding: 0.75rem 1.5rem;
}

:deep(.el-alert) {
  border-radius: 0.5rem;
}

/* 响应式设计 */
@media (max-width: 640px) {
  .cropper-content {
    padding: 1rem;
  }
  
  .cropper-header {
    padding: 1rem;
  }
  
  .controls-section {
    padding: 1rem;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .focal-coords {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .help-section {
    padding: 1rem;
  }
}
</style>
