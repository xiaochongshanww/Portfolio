<template>
  <Transition name="scroll-to-top" appear>
    <button
      v-show="isVisible"
      @click="scrollToTop"
      class="scroll-to-top-btn"
      :class="{ 'is-scrolling': isScrolling }"
      :aria-label="'回到顶部'"
      title="回到顶部"
    >
      <!-- 向上箭头图标 -->
      <div class="btn-icon">
        <svg 
          width="20" 
          height="20" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          stroke-width="2.5" 
          stroke-linecap="round" 
          stroke-linejoin="round"
          class="arrow-icon"
        >
          <path d="m18 15-6-6-6 6"/>
        </svg>
      </div>
      
      <!-- 进度圈 -->
      <svg class="progress-ring" width="60" height="60">
        <circle
          class="progress-ring__circle"
          stroke="currentColor"
          stroke-width="2"
          fill="transparent"
          r="28"
          cx="30"
          cy="30"
          :style="{ strokeDashoffset: progressOffset }"
        />
      </svg>
    </button>
  </Transition>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';

// Props
const props = defineProps({
  // 显示按钮的滚动阈值（像素）
  threshold: {
    type: Number,
    default: 400
  },
  // 滚动动画持续时间（毫秒）
  duration: {
    type: Number,
    default: 800
  },
  // 滚动动画缓动函数
  easing: {
    type: String,
    default: 'easeOutCubic' // easeOutCubic, easeInOutCubic, linear
  }
});

// 响应式数据
const isVisible = ref(false);
const isScrolling = ref(false);
const scrollY = ref(0);
const maxScrollY = ref(0);

// 计算滚动进度（用于进度圈动画）
const scrollProgress = computed(() => {
  if (maxScrollY.value === 0) return 0;
  return Math.min(scrollY.value / maxScrollY.value, 1);
});

// 计算进度圈的 stroke-dashoffset
const progressOffset = computed(() => {
  const circumference = 2 * Math.PI * 28; // r=28
  return circumference - (scrollProgress.value * circumference);
});

// 缓动函数
const easingFunctions = {
  linear: (t) => t,
  easeOutCubic: (t) => 1 - Math.pow(1 - t, 3),
  easeInOutCubic: (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
};

// 处理滚动事件
const handleScroll = () => {
  const currentScrollY = window.scrollY;
  const documentHeight = document.documentElement.scrollHeight;
  const windowHeight = window.innerHeight;
  
  scrollY.value = currentScrollY;
  maxScrollY.value = documentHeight - windowHeight;
  
  // 控制按钮显示/隐藏
  isVisible.value = currentScrollY > props.threshold;
};

// 滚动到顶部
const scrollToTop = () => {
  if (isScrolling.value) return; // 防止重复点击
  
  isScrolling.value = true;
  
  const startY = window.scrollY;
  const startTime = performance.now();
  const easeFunction = easingFunctions[props.easing] || easingFunctions.easeOutCubic;
  
  const animateScroll = (currentTime) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / props.duration, 1);
    const easedProgress = easeFunction(progress);
    
    const currentY = startY - (startY * easedProgress);
    window.scrollTo(0, currentY);
    
    if (progress < 1) {
      requestAnimationFrame(animateScroll);
    } else {
      isScrolling.value = false;
    }
  };
  
  requestAnimationFrame(animateScroll);
};

// 节流处理滚动事件
let scrollTimer = null;
const throttledHandleScroll = () => {
  if (scrollTimer) return;
  
  scrollTimer = setTimeout(() => {
    handleScroll();
    scrollTimer = null;
  }, 16); // ~60fps
};

// 生命周期
onMounted(() => {
  // 初始化
  handleScroll();
  
  // 添加滚动监听
  window.addEventListener('scroll', throttledHandleScroll, { passive: true });
  window.addEventListener('resize', handleScroll, { passive: true });
});

onUnmounted(() => {
  // 清理事件监听
  window.removeEventListener('scroll', throttledHandleScroll);
  window.removeEventListener('resize', handleScroll);
  
  // 清理定时器
  if (scrollTimer) {
    clearTimeout(scrollTimer);
  }
});
</script>

<style scoped>
/* 主按钮样式 */
.scroll-to-top-btn {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 56px;
  height: 56px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  z-index: 1000;
  
  /* 阴影效果 */
  box-shadow: 
    0 8px 25px -8px rgba(102, 126, 234, 0.4),
    0 4px 12px -4px rgba(0, 0, 0, 0.15);
  
  /* 动画过渡 */
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  /* Flexbox 居中 */
  display: flex;
  align-items: center;
  justify-content: center;
  
  /* 交互反馈 */
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

/* 悬停效果 */
.scroll-to-top-btn:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 35px -8px rgba(102, 126, 234, 0.5),
    0 8px 20px -4px rgba(0, 0, 0, 0.2);
}

/* 点击效果 */
.scroll-to-top-btn:active {
  transform: translateY(0);
  box-shadow: 
    0 6px 20px -8px rgba(102, 126, 234, 0.3),
    0 2px 8px -4px rgba(0, 0, 0, 0.15);
}

/* 滚动中状态 */
.scroll-to-top-btn.is-scrolling {
  pointer-events: none;
  opacity: 0.8;
}

/* 按钮图标 */
.btn-icon {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}

.arrow-icon {
  transition: transform 0.2s ease;
}

.scroll-to-top-btn:hover .arrow-icon {
  transform: translateY(-2px);
}

/* 进度圈 */
.progress-ring {
  position: absolute;
  top: -2px;
  left: -2px;
  width: 60px;
  height: 60px;
  transform: rotate(-90deg);
  pointer-events: none;
}

.progress-ring__circle {
  stroke-dasharray: 176; /* 2 * π * 28 ≈ 176 */
  transition: stroke-dashoffset 0.1s ease-out;
  opacity: 0.3;
}

/* 进入/离开动画 */
.scroll-to-top-enter-active {
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.scroll-to-top-leave-active {
  transition: all 0.3s cubic-bezier(0.55, 0, 0.1, 1);
}

.scroll-to-top-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.8);
}

.scroll-to-top-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.9);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .scroll-to-top-btn {
    right: 16px;
    bottom: 16px;
    width: 48px;
    height: 48px;
  }
  
  .progress-ring {
    width: 52px;
    height: 52px;
  }
  
  .arrow-icon {
    width: 18px;
    height: 18px;
  }
}

/* 减弱动画效果（适配用户偏好） */
@media (prefers-reduced-motion: reduce) {
  .scroll-to-top-btn,
  .arrow-icon,
  .progress-ring__circle {
    transition: none;
  }
  
  .scroll-to-top-enter-active,
  .scroll-to-top-leave-active {
    transition: opacity 0.2s ease;
  }
  
  .scroll-to-top-enter-from,
  .scroll-to-top-leave-to {
    transform: none;
  }
}

/* 高对比度模式适配 */
@media (prefers-contrast: high) {
  .scroll-to-top-btn {
    background: #000;
    border: 2px solid #fff;
  }
  
  .progress-ring__circle {
    opacity: 0.8;
  }
}

/* 深色主题适配 */
@media (prefers-color-scheme: dark) {
  .scroll-to-top-btn {
    background: linear-gradient(135deg, #4c63d2 0%, #5a67d8 100%);
    box-shadow: 
      0 8px 25px -8px rgba(76, 99, 210, 0.4),
      0 4px 12px -4px rgba(0, 0, 0, 0.3);
  }
  
  .scroll-to-top-btn:hover {
    box-shadow: 
      0 12px 35px -8px rgba(76, 99, 210, 0.5),
      0 8px 20px -4px rgba(0, 0, 0, 0.4);
  }
}
</style>