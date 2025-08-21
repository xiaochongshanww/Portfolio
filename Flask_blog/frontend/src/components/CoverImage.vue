<template>
  <div class="cover-image-container" :class="containerClass">
    <img 
      :src="imageUrl" 
      :alt="alt" 
      :class="imageClass"
      @error="handleImageError"
      @load="handleImageLoad"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  src: {
    type: String,
    default: ''
  },
  alt: {
    type: String,
    default: '文章封面'
  },
  containerClass: {
    type: String,
    default: ''
  },
  imageClass: {
    type: String,
    default: ''
  },
  showDefault: {
    type: Boolean,
    default: true
  }
})

const imageError = ref(false)
const imageLoaded = ref(false)

// 默认封面图路径
const DEFAULT_COVER = '/assets/images/default-cover.svg'

// 计算实际显示的图片URL
const imageUrl = computed(() => {
  // 如果有自定义封面且没有加载错误，使用自定义封面
  if (props.src && !imageError.value) {
    return props.src
  }
  
  // 如果允许显示默认封面，返回默认封面
  if (props.showDefault) {
    return DEFAULT_COVER
  }
  
  // 否则返回空（不显示图片）
  return ''
})

function handleImageError() {
  // 如果自定义图片加载失败，标记错误状态
  if (props.src) {
    imageError.value = true
  }
}

function handleImageLoad() {
  imageLoaded.value = true
  // 重置错误状态（在切换图片时）
  imageError.value = false
}

// 暴露状态给父组件
defineExpose({
  isUsingDefault: computed(() => !props.src || imageError.value),
  imageLoaded
})
</script>

<style scoped>
.cover-image-container {
  position: relative;
  overflow: hidden;
  /* 默认16:9纵横比，可被外部样式覆盖 */
  aspect-ratio: 16 / 9;
}

/* 确保图片在加载时有平滑过渡 */
.cover-image-container img {
  transition: opacity 0.3s ease;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

/* 加载态样式 */
.cover-image-container img[src=""] {
  opacity: 0;
}

/* 添加加载时的占位背景 */
.cover-image-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  opacity: 0.3;
  z-index: -1;
}
</style>