import { ref, computed, onMounted, onUnmounted } from 'vue'

/**
 * 响应式布局检测工具函数 (动态计算版本)
 * 基于容器实际可用宽度动态判断是否显示侧边栏
 */
export function useResponsiveLayout(containerElement = ref(null)) {
  // 窗口宽度
  const windowWidth = ref(window.innerWidth)
  // 容器宽度（实际可用空间）
  const containerWidth = ref(0)
  
  // 布局空间需求定义
  const LAYOUT_REQUIREMENTS = {
    articleMinWidth: 550,    // 文章列表最小宽度
    gap: 30,                 // 中间间距
    sidebarWidth: 320,       // 侧边栏宽度
    safeMargin: 60,          // 安全边距（保证右边距）
    containerPadding: 0      // 容器内边距（已移除）
  }
  
  // 计算显示侧边栏所需的最小宽度
  const requiredWidth = computed(() => {
    return Object.values(LAYOUT_REQUIREMENTS).reduce((total, width) => total + width, 0)
  })
  
  // ResizeObserver 实例
  let resizeObserver = null
  
  // 更新窗口宽度
  const updateWidth = () => {
    windowWidth.value = window.innerWidth
  }
  
  // 更新容器宽度
  const updateContainerWidth = () => {
    if (containerElement.value) {
      containerWidth.value = containerElement.value.offsetWidth || containerElement.value.clientWidth || 0
    } else {
      // 如果没有容器元素，基于窗口宽度和阶梯式容器配置估算
      let estimatedContainerWidth
      
      if (windowWidth.value >= 1400) {
        estimatedContainerWidth = 1320
      } else if (windowWidth.value >= 1200) {
        estimatedContainerWidth = 1140
      } else if (windowWidth.value >= 992) {
        estimatedContainerWidth = 960
      } else if (windowWidth.value >= 768) {
        estimatedContainerWidth = 720
      } else if (windowWidth.value >= 576) {
        estimatedContainerWidth = 540
      } else {
        estimatedContainerWidth = windowWidth.value - 32 // 减去padding
      }
      
      containerWidth.value = estimatedContainerWidth
    }
  }
  
  // 基于实际容器宽度判断是否可以显示侧边栏
  const canShowSidebar = computed(() => {
    return containerWidth.value >= requiredWidth.value
  })
  
  // 是否为移动端（与canShowSidebar相反）
  const isMobile = computed(() => {
    return !canShowSidebar.value
  })
  
  // 是否为桌面设备（与canShowSidebar相同）
  const isDesktop = computed(() => {
    return canShowSidebar.value
  })
  
  // 布局模式
  const layoutMode = computed(() => {
    return isMobile.value ? 'mobile' : 'desktop'
  })
  
  // 生命周期管理
  onMounted(() => {
    // 监听窗口变化
    window.addEventListener('resize', updateWidth)
    
    // 设置ResizeObserver监听容器变化
    if (containerElement.value) {
      resizeObserver = new ResizeObserver(() => {
        updateContainerWidth()
      })
      resizeObserver.observe(containerElement.value)
    }
    
    // 初始化时立即更新
    updateWidth()
    updateContainerWidth()
    
    // 如果容器元素还没有准备好，等一下再试
    if (!containerElement.value) {
      setTimeout(() => {
        if (containerElement.value && resizeObserver) {
          resizeObserver.observe(containerElement.value)
          updateContainerWidth()
        }
      }, 100)
    }
  })
  
  onUnmounted(() => {
    window.removeEventListener('resize', updateWidth)
    if (resizeObserver) {
      resizeObserver.disconnect()
    }
  })
  
  // 调试信息（开发环境使用）
  const debugInfo = computed(() => ({
    windowWidth: windowWidth.value,
    containerWidth: containerWidth.value,
    requiredWidth: requiredWidth.value,
    isMobile: isMobile.value,
    isDesktop: isDesktop.value,
    canShowSidebar: canShowSidebar.value,
    layoutMode: layoutMode.value,
    layoutRequirements: LAYOUT_REQUIREMENTS
  }))
  
  return {
    // 基础数据
    windowWidth,
    containerWidth,
    requiredWidth,
    
    // 布局判断
    isMobile,
    isDesktop,
    canShowSidebar,
    layoutMode,
    
    // 布局需求常量
    LAYOUT_REQUIREMENTS,
    
    // 工具方法
    updateContainerWidth,
    
    // 调试信息
    debugInfo
  }
}

/**
 * 简化版响应式检测（用于只需要基础判断的组件）
 */
export function useSimpleResponsive() {
  const { isMobile, isDesktop, windowWidth } = useResponsiveLayout()
  
  return {
    isMobile,
    isDesktop,
    windowWidth
  }
}