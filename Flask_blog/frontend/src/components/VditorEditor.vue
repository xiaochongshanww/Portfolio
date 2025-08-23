<template>
  <div class="vditor-editor-container">
    <!-- 编辑器头部信息 -->
    <div class="editor-header">
      <div class="header-info">
        <el-icon class="info-icon"><InfoFilled /></el-icon>
        <span>Markdown编辑器，支持图片上传、拖拽和粘贴</span>
      </div>
      <div class="header-actions">
        <el-select 
          v-model="currentMode" 
          size="small" 
          style="width: 120px"
          @change="changeMode"
          :key="`mode-selector-${currentMode}`"
          placeholder="选择模式"
        >
          <el-option label="所见即所得" value="wysiwyg" />  
          <el-option label="即时渲染" value="ir" />
          <el-option label="分屏预览" value="sv" />
        </el-select>
      </div>
    </div>

    <!-- Vditor编辑器容器 -->
    <div ref="vditorRef" class="vditor-container">
      <!-- 加载状态 -->
      <div v-if="!isEditorReady" class="loading-placeholder">
        <div class="loading-content">
          <el-icon class="is-loading"><Loading /></el-icon>
          <p>正在初始化Markdown编辑器...</p>
          <p class="loading-tip">首次加载可能需要几秒钟</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { InfoFilled, Loading } from '@element-plus/icons-vue';
import message from '../utils/message';
import Vditor from 'vditor';
import 'vditor/dist/index.css';
import { useUserStore } from '../stores/user';

// Props
interface Props {
  modelValue: string;
  height?: number;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  height: 500
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

// Stores
const userStore = useUserStore();

// 响应式数据
const vditorRef = ref<HTMLElement>();
const currentMode = ref<'wysiwyg' | 'ir' | 'sv'>('wysiwyg'); // 默认即时渲染模式
const isEditorReady = ref(false); // 编辑器是否准备完成
let vditor: Vditor | null = null;

// 防抖函数
function debounce<T extends (...args: any[]) => void>(func: T, wait: number): T {
  let timeout: NodeJS.Timeout | null = null;
  return ((...args: any[]) => {
    const later = () => {
      timeout = null;
      func(...args);
    };
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  }) as T;
}

// 获取上传配置（动态获取token）
function getUploadConfig() {
  return {
    url: '/api/v1/uploads/image',
    headers: {
      'Authorization': `Bearer ${userStore.token || ''}`
    },
    accept: 'image/*',
    multiple: false,
    fieldName: 'file',
    success: (editor: any, msg: string) => {
      try {
        console.log('✅ 图片上传成功:', msg);
        const response = JSON.parse(msg);
        if (response.code === 0 && response.data?.url) {
          // 智能选择最佳图片尺寸
          const data = response.data;
          let bestUrl = data.url; // 默认原图
          
          // 如果有variants，选择最适合的尺寸（编辑器内显示建议800px以下）
          if (data.variants && data.variants.length > 0) {
            // 优先级：md(800px) > sm(400px) > lg(1600px) > 原图
            const mdVariant = data.variants.find(v => v.label === 'md');
            const smVariant = data.variants.find(v => v.label === 'sm');
            
            if (mdVariant) {
              bestUrl = mdVariant.url;
              console.log('使用md尺寸图片:', bestUrl);
            } else if (smVariant) {
              bestUrl = smVariant.url; 
              console.log('使用sm尺寸图片:', bestUrl);
            }
          }
          
          // 直接插入图片，Vditor的success回调时机是合适的
          const imageMarkdown = `![图片](${bestUrl})`;
          console.log('准备插入图片:', imageMarkdown);
          console.log('编辑器状态:', { vditor: !!vditor, isReady: isEditorReady.value });
          
          if (vditor && isEditorReady.value) {
            try {
              // 在前后添加换行符，确保图片独占一行
              vditor.insertValue('\n' + imageMarkdown + '\n');
              console.log('✅ 图片已成功插入编辑器');
            } catch (error) {
              console.error('❌ 插入图片时出错:', error);
              // 备用方案：直接插入不带换行符
              try {
                vditor.insertValue(imageMarkdown);
                console.log('✅ 使用备用方案插入图片');
              } catch (fallbackError) {
                console.error('❌ 备用方案也失败:', fallbackError);
                message.critical('图片插入失败，请手动粘贴图片链接');
              }
            }
          } else {
            console.warn('⚠️ 编辑器未就绪，无法插入图片');
            console.log('调试信息:', { 
              hasVditor: !!vditor, 
              isReady: isEditorReady.value,
              vditorValue: vditor ? 'exists' : 'null'
            });
            message.warning('编辑器未就绪，请稍后再试');
          }
          
          message.success({
            message: '图片上传成功',
            duration: 2000,
            showClose: false
          });
          
          // 尝试让Vditor自己处理插入：返回包含图片URL的JSON字符串
          return JSON.stringify({
            "msg": "",
            "code": 0,
            "data": {
              "errFiles": [],
              "succMap": {
                [data.url]: bestUrl
              }
            }
          });
        } else {
          console.error('上传响应格式错误:', response);
          message.critical('图片上传失败: ' + (response.message || '响应格式错误'));
        }
      } catch (error) {
        console.error('解析上传响应失败:', error, msg);
        message.critical('图片上传失败: 响应解析错误');
      }
    },
    error: (msg: string) => {
      console.error('❌ 图片上传失败:', msg);
      message.critical('图片上传失败: ' + msg);
    }
  };
}

// 初始化Vditor
async function initVditor() {
  if (!vditorRef.value) {
    console.error('Vditor容器元素不存在');
    return;
  }

  try {
    console.log('🔄 VditorEditor: 开始初始化Vditor编辑器...');
    
    // 确保容器有ID
    if (!vditorRef.value.id) {
      vditorRef.value.id = `vditor-${Date.now()}`;
    }
    
    vditor = new Vditor(vditorRef.value, {
      // 基础配置
      height: props.height,
      mode: currentMode.value,
      theme: 'classic',
      
      // 编辑器配置
      placeholder: '支持Markdown编写，可粘贴文本内容，点击上传或拖拽图片...',
      
      // 工具栏配置（包含图片上传）
      toolbar: [
        'headings',
        'bold',
        'italic',
        'strike',
        '|',
        'line',
        'quote',
        '|',
        'list',
        'ordered-list',
        'check',
        '|',
        'code',
        'inline-code',
        'link',
        'upload',
        'table',
        '|',
        'undo',
        'redo',
        'fullscreen'
      ],
      
      // 缓存配置
      cache: {
        enable: false
      },
      
      // 性能优化配置
      preview: {
        delay: 300, // 预览延迟，减少频繁渲染
        maxWidth: 800, // 限制预览区域最大宽度
        theme: {
          path: undefined // 不加载额外主题，减少资源消耗
        }
      },
      
      // 图片相关性能配置
      image: {
        isPreview: true, // 启用图片预览
        preview: {
          delay: 100 // 图片预览延迟
        }
      },
      
      // 图片上传配置
      upload: getUploadConfig(),
      
      // 事件回调（添加防抖优化）
      input: debounce((value: string) => {
        emit('update:modelValue', value);
      }, 300), // 300ms防抖，减少频繁更新
      
      focus: (value: string) => {
        console.log('编辑器获得焦点，当前内容长度:', value.length);
      },
      
      blur: (value: string) => {
        console.log('编辑器失去焦点，当前内容长度:', value.length);
      },
      
      after: () => {
        console.log('✅ Vditor初始化完成');
        
        // 将状态更新延迟到下一个宏任务，避免与Vditor的DOM操作冲突
        setTimeout(() => {
          // 安全检查：如果组件已被卸载，不要设置状态
          if (!vditorRef.value) {
            console.log('Vditor初始化完成但组件已卸载，跳过状态设置');
            return;
          }
          
          // 使用nextTick确保在Vue更新周期外更新状态
          nextTick(() => {
            try {
              isEditorReady.value = true; // 标记编辑器已准备完成
              
              // 设置初始内容
              if (props.modelValue) {
                console.log('设置初始内容:', props.modelValue.substring(0, 100));
                try {
                  vditor?.setValue(props.modelValue);
                } catch (e) {
                  console.warn('设置初始内容失败，可能组件正在卸载:', e);
                }
              }
            } catch (error) {
              console.warn('Vditor初始化后状态更新失败:', error);
            }
          });
        }, 50);
        
        // 验证编辑器是否正确创建
        try {
          if (vditor && vditorRef.value?.querySelector('.vditor-content')) {
            message.success('Markdown编辑器加载完成！');
          } else {
            console.error('编辑器初始化异常');
            message.critical('编辑器加载异常，请刷新重试');
          }
        } catch (e) {
          console.warn('编辑器验证过程中出错，可能组件正在卸载:', e);
        }
      }
    });
    
  } catch (error) {
    console.error('❌ 初始化Vditor失败:', error);
    console.error('错误详情:', error.message);
    console.error('错误堆栈:', error.stack);
    message.critical('编辑器初始化失败: ' + error.message);
    
    // 将编辑器标记为未准备状态
    isEditorReady.value = false;
  }
}

// forceResetEditorStyles 函数已删除，让Vditor保持原生样式

// 切换编辑模式
function changeMode() {
  if (vditor && isEditorReady.value) {
    // 获取当前内容
    const currentValue = vditor.getValue();
    console.log(`切换到 ${currentMode.value} 模式，保存内容长度:`, currentValue.length);
    
    // 标记为未准备状态
    isEditorReady.value = false;
    
    // 销毁当前编辑器
    try {
      vditor.destroy();
    } catch (error) {
      console.warn('销毁编辑器时出错:', error);
    }
    vditor = null;
    
    // 重新初始化
    setTimeout(() => {
      initVditor().then(() => {
        // 等待编辑器完全初始化后恢复内容
        setTimeout(() => {
          if (currentValue && vditor && isEditorReady.value) {
            vditor.setValue(currentValue);
            console.log('恢复内容完成');
          }
        }, 200);
      });
    }, 100);
  }
}


// 监听props变化
watch(() => props.modelValue, (newValue) => {
  if (vditor && isEditorReady.value && newValue !== vditor.getValue()) {
    try {
      vditor.setValue(newValue || '');
    } catch (error) {
      console.warn('VditorEditor: 更新内容时出错，可能组件正在卸载:', error);
    }
  }
});

// 生命周期
onMounted(() => {
  console.log('🔀 VditorEditor: 组件onMounted触发');
  
  // 添加Vditor相关的错误处理
  const handleVditorError = (event) => {
    if (event.reason && event.reason.message && 
        (event.reason.message.includes('insertBefore') || 
         event.reason.message.includes('removeChild') ||
         event.reason.message.includes('Vditor'))) {
      console.warn('检测到Vditor相关错误，已静默处理:', event.reason.message);
      // 不调用preventDefault()，避免干扰其他系统功能
    }
  };
  
  window.addEventListener('unhandledrejection', handleVditorError);
  
  // 清理函数
  const cleanup = () => {
    window.removeEventListener('unhandledrejection', handleVditorError);
  };
  
  // 保存清理函数到组件实例
  window.vditorErrorCleanup = cleanup;
  
  // 设置初始化超时
  const initTimeout = setTimeout(() => {
    if (!isEditorReady.value) {
      console.error('⏰ Vditor初始化超时');
      message.critical('编辑器初始化超时，请刷新页面重试');
    }
  }, 10000); // 10秒超时
  
  nextTick(() => {
    console.log('🔀 VditorEditor: nextTick后准备初始化');
    // 添加安全检查，防止在组件即将卸载时初始化
    if (!vditorRef.value) {
      console.log('🔀 VditorEditor: 容器不存在，跳过初始化');
      clearTimeout(initTimeout);
      return;
    }
    
    initVditor().then(() => {
      clearTimeout(initTimeout);
    }).catch((error) => {
      clearTimeout(initTimeout);
      console.error('初始化失败:', error);
    });
  });
});

onBeforeUnmount(() => {
  console.log('🔄 VditorEditor: 开始卸载组件');
  
  // 标记编辑器为非准备状态，避免其他操作
  isEditorReady.value = false;
  
  if (vditor) {
    try {
      console.log('🔄 VditorEditor: 销毁Vditor实例');
      vditor.destroy();
      console.log('🔄 VditorEditor: Vditor实例销毁成功');
    } catch (error) {
      console.error('🔄 VditorEditor: 销毁Vditor失败:', error);
    }
  }
  
  // 清空实例引用
  vditor = null;
  
  // 清理Vditor错误处理
  if (window.vditorErrorCleanup) {
    window.vditorErrorCleanup();
    delete window.vditorErrorCleanup;
  }
  
  console.log('🔄 VditorEditor: 组件卸载完成');
});

// 暴露方法给父组件
defineExpose({
  syncContent() {
    if (vditor && isEditorReady.value) {
      try {
        const content = vditor.getValue();
        console.log('VditorEditor syncContent called, content length:', content?.length || 0);
        return content || '';
      } catch (error) {
        console.error('VditorEditor syncContent error:', error);
        return '';
      }
    }
    console.warn('VditorEditor syncContent called but editor not ready');
    return '';
  },
  getContent() {
    if (vditor && isEditorReady.value) {
      try {
        return vditor.getValue() || '';
      } catch (error) {
        console.warn('VditorEditor getContent error:', error);
        return '';
      }
    }
    return '';
  },
  setContent(content: string) {
    if (vditor && isEditorReady.value) {
      try {
        vditor.setValue(content);
      } catch (error) {
        console.warn('VditorEditor setContent error:', error);
      }
    }
  },
  insertValue(value: string) {
    if (vditor && isEditorReady.value) {
      try {
        vditor.insertValue(value);
      } catch (error) {
        console.warn('VditorEditor insertValue error:', error);
      }
    }
  },
  focus() {
    if (vditor && isEditorReady.value) {
      try {
        vditor.focus();
      } catch (error) {
        console.warn('VditorEditor focus error:', error);
      }
    }
  },
  getHTML() {
    if (vditor && isEditorReady.value) {
      try {
        return vditor.getHTML() || '';
      } catch (error) {
        console.warn('VditorEditor getHTML error:', error);
        return '';
      }
    }
    return '';
  }
});
</script>

<style scoped>
.vditor-editor-container {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
}

.info-icon {
  color: #3b82f6;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.vditor-container {
  position: relative;
  min-height: 500px;
}

.loading-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  background: #fafafa;
}

.loading-content {
  text-align: center;
  color: #666;
}

.loading-content .el-icon {
  font-size: 32px;
  color: #409eff;
  margin-bottom: 16px;
}

.loading-content p {
  margin: 8px 0;
  font-size: 16px;
}

.loading-tip {
  font-size: 14px;
  color: #999;
}

/* Vditor基础样式覆盖 - 最小干预原则 */
:deep(.vditor) {
  border: none !important;
  border-radius: 0 !important;
}

/* 即时渲染模式优化 */
:deep(.vditor-ir .vditor-reset) {
  padding: 16px !important;
  font-size: 16px !important;
  line-height: 1.6 !important;
}

/* 分屏预览模式优化 */
:deep(.vditor-sv .vditor-reset) {
  padding: 16px !important;
  font-size: 16px !important;
  line-height: 1.6 !important;
}

/* 所见即所得模式优化 */
:deep(.vditor-wysiwyg .vditor-reset) {
  padding: 16px !important;
  font-size: 16px !important;
  line-height: 1.6 !important;
}

/* 图片性能优化样式 */
:deep(.vditor-reset img) {
  /* 限制编辑器内图片最大宽度，避免大图卡顿 */
  max-width: 100% !important;
  height: auto !important;
  /* 启用硬件加速 */
  transform: translateZ(0);
  /* 优化图片渲染质量 */
  image-rendering: -webkit-optimize-contrast;
  image-rendering: optimize-contrast;
  /* 平滑过渡 */
  transition: opacity 0.3s ease;
  /* 懒加载属性 */
  loading: lazy;
}

/* 图片加载状态优化 */
:deep(.vditor-reset img[src=""]) {
  opacity: 0.5;
  background: #f5f5f5;
}

/* Element Plus Select样式优化 */
:deep(.el-select) {
  --el-select-input-focus-border-color: #409eff;
}

:deep(.el-select__wrapper) {
  transition: all 0.2s ease;
}

:deep(.el-select__wrapper.is-focused) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

/* 优化下拉选项样式，减少!important的使用 */
:deep(.el-select-dropdown__item) {
  transition: all 0.2s ease;
  position: relative;
}

:deep(.el-select-dropdown__item.is-selected) {
  background-color: #409eff;
  color: #ffffff;
  font-weight: 600;
}

:deep(.el-select-dropdown__item:not(.is-selected):hover) {
  background-color: #f5f7fa;
  color: #606266;
}

:deep(.el-select-dropdown__item.is-selected:hover) {
  background-color: #337ecc;
  color: #ffffff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .editor-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .header-info {
    justify-content: center;
    text-align: center;
  }
  
  .header-actions {
    justify-content: center;
  }
}
</style>