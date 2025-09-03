<template>
  <div class="vditor-editor-container">
    <!-- 编辑器头部信息 -->
    <div class="editor-header">
      <div class="header-info">
        <el-icon class="info-icon"><InfoFilled /></el-icon>
        <span>Markdown编辑器，支持图片上传、拖拽、粘贴和从媒体库选择</span>
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

    <!-- 原生媒体选择模态框将通过JavaScript动态创建 -->
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { InfoFilled, Loading } from '@element-plus/icons-vue';
import message from '../utils/message';
import Vditor from 'vditor';
import 'vditor/dist/index.css';
import { useUserStore } from '../stores/user';
// MediaSelector组件已用原生JavaScript实现

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

// 获取上传配置（使用媒体库API）
function getUploadConfig() {
  return {
    url: '/api/v1/media/upload',
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
          let altText = data.alt_text || data.title || data.original_name || '图片';
          
          // 处理媒体库的变体格式
          if (data.variants) {
            // 如果variants是数组格式（旧格式）
            if (Array.isArray(data.variants)) {
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
            // 如果variants是对象格式（新的媒体库格式）
            else if (data.variants.variants && Array.isArray(data.variants.variants)) {
              const mdVariant = data.variants.variants.find(v => v.label === 'md');
              const smVariant = data.variants.variants.find(v => v.label === 'sm');
              
              if (mdVariant) {
                bestUrl = mdVariant.url;
                console.log('使用md尺寸图片（媒体库格式）:', bestUrl);
              } else if (smVariant) {
                bestUrl = smVariant.url; 
                console.log('使用sm尺寸图片（媒体库格式）:', bestUrl);
              }
            }
          }
          
          // 直接插入图片，Vditor的success回调时机是合适的
          const imageMarkdown = `![${altText}](${bestUrl})`;
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

// 上传单个图片文件的功能函数
async function uploadImageFile(file: File): Promise<string | null> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/v1/media/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userStore.token || ''}`
      },
      body: formData
    });
    
    const result = await response.json();
    
    if (result.code === 0 && result.data?.url) {
      // 智能选择最佳图片尺寸
      const data = result.data;
      let bestUrl = data.url; // 默认原图
      
      // 处理媒体库的变体格式
      if (data.variants) {
        // 如果variants是数组格式（旧格式）
        if (Array.isArray(data.variants)) {
          const mdVariant = data.variants.find(v => v.label === 'md');
          const smVariant = data.variants.find(v => v.label === 'sm');
          
          if (mdVariant) {
            bestUrl = mdVariant.url;
          } else if (smVariant) {
            bestUrl = smVariant.url; 
          }
        } 
        // 如果variants是对象格式（新的媒体库格式）
        else if (data.variants.variants && Array.isArray(data.variants.variants)) {
          const mdVariant = data.variants.variants.find(v => v.label === 'md');
          const smVariant = data.variants.variants.find(v => v.label === 'sm');
          
          if (mdVariant) {
            bestUrl = mdVariant.url;
          } else if (smVariant) {
            bestUrl = smVariant.url; 
          }
        }
      }
      
      console.log('✅ 图片上传成功:', bestUrl);
      return bestUrl;
    } else {
      console.error('上传响应格式错误:', result);
      message.error('图片上传失败: ' + (result.message || '响应格式错误'));
      return null;
    }
  } catch (error) {
    console.error('❌ 图片上传失败:', error);
    message.error('图片上传失败: ' + error.message);
    return null;
  }
}

// 处理粘贴内容中的本地图片路径
async function processMarkdownImages(content: string): Promise<string> {
  // 匹配markdown中的图片语法：![alt](path)
  const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
  const matches = Array.from(content.matchAll(imageRegex));
  
  if (matches.length === 0) {
    return content;
  }
  
  let processedContent = content;
  const uploadPromises = [];
  
  for (const match of matches) {
    const [fullMatch, altText, imagePath] = match;
    
    // 检测是否是本地文件路径（Windows或Linux路径格式）
    const isLocalPath = (
      // Windows路径: C:\path\to\image.jpg 或 .\relative\path.jpg
      /^[A-Za-z]:[\\\/]/.test(imagePath) ||
      /^\.?[\\\/]/.test(imagePath) ||
      // 或者不是HTTP(S)协议的路径
      (!imagePath.startsWith('http://') && !imagePath.startsWith('https://') && !imagePath.startsWith('/'))
    );
    
    if (isLocalPath) {
      console.log('检测到本地图片路径:', imagePath);
      
      // 尝试读取本地文件（使用File API）
      try {
        // 创建一个Promise来处理文件读取和上传
        const uploadPromise = (async () => {
          try {
            // 由于浏览器安全限制，我们不能直接读取本地文件系统
            // 这里我们只能处理通过拖拽或粘贴进来的文件
            // 对于markdown中的本地路径，我们给用户一个友好提示
            const placeholder = `![${altText || '图片'}](本地图片-请拖拽或粘贴图片文件)`;
            processedContent = processedContent.replace(fullMatch, placeholder);
            
            // 给用户一个提示
            message.warning({
              message: `检测到本地图片路径: ${imagePath.substring(0, 50)}${imagePath.length > 50 ? '...' : ''}。请直接拖拽或粘贴图片文件到编辑器中。`,
              duration: 5000,
              showClose: true
            });
          } catch (error) {
            console.error('处理本地图片路径失败:', error);
            // 保持原内容不变
          }
        })();
        
        uploadPromises.push(uploadPromise);
      } catch (error) {
        console.error('读取本地文件失败:', error);
      }
    }
  }
  
  // 等待所有上传完成
  if (uploadPromises.length > 0) {
    await Promise.all(uploadPromises);
  }
  
  return processedContent;
}

// 设置粘贴事件处理器
function setupPasteHandler() {
  if (!vditorRef.value || !vditor) {
    console.warn('setupPasteHandler: 编辑器未就绪');
    return;
  }

  // 寻找编辑器的实际文本输入区域
  const editorElement = vditorRef.value.querySelector('.vditor-reset') || 
                       vditorRef.value.querySelector('.vditor-content') ||
                       vditorRef.value;
  
  if (!editorElement) {
    console.warn('setupPasteHandler: 无法找到编辑器输入区域');
    return;
  }

  const handlePaste = async (event: ClipboardEvent) => {
    console.log('检测到粘贴事件');
    
    const clipboardData = event.clipboardData;
    if (!clipboardData) return;

    // 检查是否有图片文件
    const files = Array.from(clipboardData.files);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    if (imageFiles.length > 0) {
      console.log('检测到粘贴的图片文件:', imageFiles.length, '个');
      
      // 阻止默认粘贴行为
      event.preventDefault();
      
      // 上传图片文件
      for (const imageFile of imageFiles) {
        try {
          console.log('正在上传图片:', imageFile.name, imageFile.type);
          message.info(`正在上传图片: ${imageFile.name}`);
          
          const imageUrl = await uploadImageFile(imageFile);
          if (imageUrl) {
            const imageMarkdown = `![${imageFile.name}](${imageUrl})`;
            vditor?.insertValue('\n' + imageMarkdown + '\n');
            console.log('✅ 图片已插入编辑器:', imageUrl);
          }
        } catch (error) {
          console.error('上传图片失败:', error);
          message.error(`上传图片失败: ${imageFile.name}`);
        }
      }
      
      return;
    }

    // 检查是否有文本内容
    const text = clipboardData.getData('text/plain');
    if (text) {
      console.log('检测到粘贴的文本内容，长度:', text.length);
      
      // 检查是否包含本地图片路径
      const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
      const hasImages = imageRegex.test(text);
      
      if (hasImages) {
        console.log('文本内容包含markdown图片语法');
        
        // 阻止默认粘贴行为
        event.preventDefault();
        
        try {
          // 处理markdown中的本地图片路径
          const processedText = await processMarkdownImages(text);
          
          // 插入处理后的内容
          vditor?.insertValue(processedText);
          
          console.log('✅ 已插入处理后的markdown内容');
        } catch (error) {
          console.error('处理markdown内容失败:', error);
          // 如果处理失败，插入原始内容
          vditor?.insertValue(text);
        }
      }
      // 如果没有图片，让Vditor正常处理文本粘贴
    }
  };

  // 添加事件监听器
  editorElement.addEventListener('paste', handlePaste);
  console.log('✅ 粘贴事件监听器已设置');

  // 保存清理函数
  if (!window.vditorCleanupFunctions) {
    window.vditorCleanupFunctions = [];
  }
  
  const cleanup = () => {
    editorElement.removeEventListener('paste', handlePaste);
    console.log('✅ 粘贴事件监听器已清理');
  };
  
  window.vditorCleanupFunctions.push(cleanup);
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
    
    // 创建原生媒体选择模态框函数
    (window as any).openMediaLibrary = () => {
      console.log('🚀 打开原生媒体选择模态框');
      createNativeMediaModal();
    };
    
    vditor = new Vditor(vditorRef.value, {
      // 基础配置
      height: props.height,
      mode: currentMode.value,
      theme: 'classic',
      
      // 编辑器配置
      placeholder: '支持Markdown编写，可粘贴文本内容和图片，点击上传或拖拽图片...',
      
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
        {
          name: 'media-library',
          tipPosition: 'n',
          tip: '从媒体库选择',
          className: 'vditor-tooltipped vditor-tooltipped--n',
          icon: '<svg viewBox="0 0 1024 1024"><path d="M853.333 469.333A42.667 42.667 0 0 0 896 426.667v-256A42.667 42.667 0 0 0 853.333 128H170.667A42.667 42.667 0 0 0 128 170.667v256a42.667 42.667 0 0 0 42.667 42.666h682.666z m-42.666-85.333H213.333v-170.667h597.334V384z m42.666 213.333A42.667 42.667 0 0 0 896 554.667v-42.667a42.667 42.667 0 0 0-85.333 0v42.667H213.333v-42.667a42.667 42.667 0 0 0-85.333 0v42.667A42.667 42.667 0 0 0 170.667 640h682.666z m0 256A42.667 42.667 0 0 0 896 832v-42.667a42.667 42.667 0 0 0-85.333 0V832H213.333v-42.667a42.667 42.667 0 0 0-85.333 0V832A42.667 42.667 0 0 0 170.667 896h682.666z"/></svg>',
          click: (event?: Event) => {
            console.log('📱 媒体库工具栏按钮被点击');
            // 阻止事件冒泡，避免潜在的事件冲突
            if (event) {
              event.preventDefault();
              event.stopPropagation();
            }
            
            try {
              if (typeof (window as any).openMediaLibrary === 'function') {
                (window as any).openMediaLibrary();
              } else {
                console.error('❌ 全局媒体库函数未找到或不是函数');
                console.log('window.openMediaLibrary:', (window as any).openMediaLibrary);
              }
            } catch (error) {
              console.error('❌ 调用媒体库函数失败:', error);
              console.error('错误堆栈:', error.stack);
            }
          }
        },
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
              
              // 添加粘贴事件监听
              setupPasteHandler();
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

// 原生JavaScript媒体选择模态框
function createNativeMediaModal() {
  // 检查是否已存在模态框
  const existingModal = document.getElementById('native-media-modal');
  if (existingModal) {
    existingModal.remove();
  }

  // 创建模态框容器
  const modal = document.createElement('div');
  modal.id = 'native-media-modal';
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
  `;

  // 创建模态框内容
  const content = document.createElement('div');
  content.style.cssText = `
    background: white;
    border-radius: 8px;
    width: 600px;
    max-height: 70vh;
    overflow-y: auto;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  `;

  content.innerHTML = `
    <div style="padding: 20px; border-bottom: 1px solid #e4e7ed;">
      <h3 style="margin: 0; color: #303133; font-size: 18px;">选择媒体文件</h3>
      <div style="margin-top: 12px;">
        <button id="browse-tab" style="padding: 8px 16px; background: #409eff; color: white; border: none; border-radius: 4px 0 0 4px; cursor: pointer; font-size: 14px;">浏览媒体库</button>
        <button id="upload-tab" style="padding: 8px 16px; background: #f5f7fa; color: #606266; border: 1px solid #dcdfe6; border-radius: 0 4px 4px 0; cursor: pointer; font-size: 14px;">上传新文件</button>
      </div>
    </div>
    
    <div id="browse-content" style="padding: 0;">
      <!-- 搜索栏 -->
      <div style="padding: 20px; border-bottom: 1px solid #e4e7ed;">
        <input type="text" id="search-input" placeholder="搜索图片..." style="width: 100%; padding: 8px 12px; border: 1px solid #dcdfe6; border-radius: 4px; font-size: 14px;">
      </div>
      
      <!-- 媒体文件网格 -->
      <div id="media-loading" style="text-align: center; padding: 40px; color: #909399;">
        <div style="font-size: 32px; margin-bottom: 16px;">⏳</div>
        <div>加载中...</div>
      </div>
      
      <div id="media-grid" style="padding: 20px; display: none;">
        <div id="media-items" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; margin-bottom: 20px;">
          <!-- 媒体项目将在这里动态插入 -->
        </div>
        
        <!-- 分页 -->
        <div id="pagination" style="text-align: center; margin-top: 20px;">
          <!-- 分页控件将在这里动态插入 -->
        </div>
      </div>
      
      <!-- 空状态 -->
      <div id="empty-state" style="text-align: center; padding: 60px 20px; display: none;">
        <div style="font-size: 48px; color: #c0c4cc; margin-bottom: 16px;">📷</div>
        <div style="color: #909399; font-size: 16px; margin-bottom: 8px;">暂无媒体文件</div>
        <div style="color: #c0c4cc; font-size: 14px;">点击"上传新文件"添加第一张图片</div>
      </div>
    </div>
    
    <div id="upload-content" style="padding: 30px; display: none;">
      <!-- 上传区域 -->
      <div style="border: 2px dashed #d9d9d9; border-radius: 6px; text-align: center; padding: 40px; margin-bottom: 30px; transition: border-color 0.3s;" id="upload-area">
        <div style="font-size: 48px; color: #409eff; margin-bottom: 16px;">📁</div>
        <div style="color: #303133; font-size: 16px; margin-bottom: 8px;">将图片拖到此处，或<span style="color: #409eff; cursor: pointer;" id="click-upload">点击上传</span></div>
        <div style="color: #909399; font-size: 14px;">支持 JPG、PNG、WebP 格式，单个文件不超过 2MB</div>
        <input type="file" id="file-input" accept="image/*" style="display: none;">
      </div>
      
      <!-- 分隔线 -->
      <div style="text-align: center; margin: 30px 0; position: relative;">
        <div style="position: absolute; top: 50%; left: 0; right: 0; height: 1px; background: #e4e7ed; z-index: 1;"></div>
        <span style="background: white; padding: 0 16px; color: #909399; font-size: 14px; position: relative; z-index: 2;">或者</span>
      </div>
      
      <!-- URL输入 -->
      <div style="margin-top: 20px;">
        <div style="display: flex; gap: 8px;">
          <input type="text" id="image-url" placeholder="输入图片链接" style="flex: 1; padding: 8px 12px; border: 1px solid #dcdfe6; border-radius: 4px; font-size: 14px;">
          <button id="insert-url" style="padding: 8px 16px; background: #409eff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">插入</button>
        </div>
      </div>
      
      <!-- 上传进度 -->
      <div id="upload-progress" style="margin-top: 20px; display: none;">
        <div style="background: #f0f9ff; border: 1px solid #409eff; border-radius: 4px; padding: 12px; color: #409eff;">
          <div>正在上传...</div>
        </div>
      </div>
    </div>
    
    <div style="padding: 15px 20px; border-top: 1px solid #e4e7ed; display: flex; justify-content: space-between; align-items: center;">
      <div id="selection-info" style="color: #606266; font-size: 14px;"></div>
      <div>
        <button id="cancel-btn" style="padding: 8px 16px; background: white; color: #606266; border: 1px solid #dcdfe6; border-radius: 4px; cursor: pointer; margin-right: 12px;">取消</button>
        <button id="select-btn" style="padding: 8px 16px; background: #409eff; color: white; border: none; border-radius: 4px; cursor: pointer; display: none;">选择</button>
      </div>
    </div>
  `;

  modal.appendChild(content);
  document.body.appendChild(modal);

  // 绑定事件处理器
  setupModalEventHandlers(modal);
}

function setupModalEventHandlers(modal: HTMLElement) {
  const browseTab = modal.querySelector('#browse-tab') as HTMLElement;
  const uploadTab = modal.querySelector('#upload-tab') as HTMLElement;
  const browseContent = modal.querySelector('#browse-content') as HTMLElement;
  const uploadContent = modal.querySelector('#upload-content') as HTMLElement;
  const searchInput = modal.querySelector('#search-input') as HTMLInputElement;
  const mediaItems = modal.querySelector('#media-items') as HTMLElement;
  const cancelBtn = modal.querySelector('#cancel-btn') as HTMLElement;
  const selectBtn = modal.querySelector('#select-btn') as HTMLElement;
  const selectionInfo = modal.querySelector('#selection-info') as HTMLElement;
  
  // 上传相关元素
  const fileInput = modal.querySelector('#file-input') as HTMLInputElement;
  const uploadArea = modal.querySelector('#upload-area') as HTMLElement;
  const clickUpload = modal.querySelector('#click-upload') as HTMLElement;
  const imageUrlInput = modal.querySelector('#image-url') as HTMLInputElement;
  const insertUrlBtn = modal.querySelector('#insert-url') as HTMLElement;
  const progressDiv = modal.querySelector('#upload-progress') as HTMLElement;

  let selectedMedia: any = null;
  let currentPage = 1;
  let mediaData: any[] = [];

  // 关闭模态框
  const closeModal = () => {
    modal.remove();
  };

  // 点击背景关闭
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  // 取消按钮
  cancelBtn.addEventListener('click', closeModal);
  
  // 选择按钮
  selectBtn.addEventListener('click', () => {
    if (selectedMedia && vditor) {
      let imageUrl = selectedMedia.url;
      const altText = selectedMedia.alt_text || selectedMedia.title || selectedMedia.original_name || '图片';
      
      // 选择合适的尺寸
      if (selectedMedia.variants?.variants) {
        const mdVariant = selectedMedia.variants.variants.find((v: any) => v.label === 'md');
        const smVariant = selectedMedia.variants.variants.find((v: any) => v.label === 'sm');
        
        if (mdVariant) {
          imageUrl = mdVariant.url;
        } else if (smVariant) {
          imageUrl = smVariant.url;
        }
      }
      
      const markdown = `![${altText}](${imageUrl})`;
      vditor.insertValue('\n' + markdown + '\n');
      showNativeMessage('图片插入成功！', 'success');
      closeModal();
    }
  });

  // 标签切换
  browseTab.addEventListener('click', () => {
    browseTab.style.background = '#409eff';
    browseTab.style.color = 'white';
    browseTab.style.border = 'none';
    
    uploadTab.style.background = '#f5f7fa';
    uploadTab.style.color = '#606266';
    uploadTab.style.border = '1px solid #dcdfe6';
    
    browseContent.style.display = 'block';
    uploadContent.style.display = 'none';
    
    // 加载媒体数据
    loadMediaData();
  });
  
  uploadTab.addEventListener('click', () => {
    uploadTab.style.background = '#409eff';
    uploadTab.style.color = 'white';
    uploadTab.style.border = 'none';
    
    browseTab.style.background = '#f5f7fa';
    browseTab.style.color = '#606266';
    browseTab.style.border = '1px solid #dcdfe6';
    
    browseContent.style.display = 'none';
    uploadContent.style.display = 'block';
  });

  // 搜索功能
  let searchTimeout: NodeJS.Timeout;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentPage = 1;
      loadMediaData();
    }, 500);
  });

  // 加载媒体数据
  const loadMediaData = async () => {
    const mediaLoading = modal.querySelector('#media-loading') as HTMLElement;
    const mediaGrid = modal.querySelector('#media-grid') as HTMLElement;
    const emptyState = modal.querySelector('#empty-state') as HTMLElement;
    
    mediaLoading.style.display = 'block';
    mediaGrid.style.display = 'none';
    emptyState.style.display = 'none';
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        size: '20',
        type: 'image',
        keyword: searchInput.value || ''
      });
      
      const response = await fetch(`/api/v1/media?${params}`, {
        headers: {
          'Authorization': `Bearer ${userStore.token}`
        }
      });
      
      const result = await response.json();
      let data = result;
      
      // 处理嵌套响应格式
      if (result.code === 0 && result.data) {
        data = result.data;
      }
      
      mediaData = data.items || data.media || [];
      
      mediaLoading.style.display = 'none';
      
      if (mediaData.length === 0) {
        emptyState.style.display = 'block';
      } else {
        mediaGrid.style.display = 'block';
        renderMediaItems();
      }
      
    } catch (error) {
      console.error('加载媒体数据失败:', error);
      mediaLoading.style.display = 'none';
      emptyState.style.display = 'block';
      showNativeMessage('加载媒体文件失败', 'error');
    }
  };

  // 渲染媒体项目
  const renderMediaItems = () => {
    mediaItems.innerHTML = '';
    
    mediaData.forEach((media: any) => {
      const itemElement = document.createElement('div');
      itemElement.style.cssText = `
        position: relative;
        aspect-ratio: 1;
        border: 2px solid #e4e7ed;
        border-radius: 6px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.2s;
        background: #f8f9fa;
      `;
      
      itemElement.addEventListener('mouseenter', () => {
        itemElement.style.borderColor = '#409eff';
        itemElement.style.transform = 'translateY(-2px)';
        itemElement.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
      });
      
      itemElement.addEventListener('mouseleave', () => {
        if (selectedMedia?.id !== media.id) {
          itemElement.style.borderColor = '#e4e7ed';
          itemElement.style.transform = 'translateY(0)';
          itemElement.style.boxShadow = 'none';
        }
      });
      
      itemElement.addEventListener('click', () => {
        // 取消之前选中的项目
        if (selectedMedia) {
          const prevSelected = modal.querySelector(`[data-media-id="${selectedMedia.id}"]`);
          if (prevSelected) {
            prevSelected.style.borderColor = '#e4e7ed';
            prevSelected.style.background = '#f8f9fa';
          }
        }
        
        // 选中当前项目
        selectedMedia = media;
        itemElement.style.borderColor = '#409eff';
        itemElement.style.background = '#f0f9ff';
        
        // 显示选择按钮和信息
        selectBtn.style.display = 'inline-block';
        selectionInfo.textContent = `已选择：${media.title || media.original_name}`;
      });
      
      itemElement.setAttribute('data-media-id', media.id.toString());
      
      // 获取预览图片
      let previewUrl = media.url;
      if (media.variants?.variants) {
        const thumbVariant = media.variants.variants.find((v: any) => v.label === 'thumb' || v.label === 'sm');
        if (thumbVariant) {
          previewUrl = thumbVariant.url;
        }
      }
      
      itemElement.innerHTML = `
        <img 
          src="${previewUrl}" 
          alt="${media.alt_text || media.title || ''}"
          style="width: 100%; height: 100%; object-fit: cover;"
          onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
        >
        <div style="display: none; width: 100%; height: 100%; align-items: center; justify-content: center; color: #909399; font-size: 24px;">
          📷
        </div>
      `;
      
      mediaItems.appendChild(itemElement);
    });
  };

  // 初始加载媒体数据
  loadMediaData();

  // 上传相关事件处理器
  clickUpload.addEventListener('click', () => {
    fileInput.click();
  });

  // 拖拽上传
  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#409eff';
    uploadArea.style.backgroundColor = '#f0f9ff';
  });

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = '#d9d9d9';
    uploadArea.style.backgroundColor = '';
  });

  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#d9d9d9';
    uploadArea.style.backgroundColor = '';
    
    const files = e.dataTransfer?.files;
    if (files && files[0]) {
      handleFileUpload(files[0], progressDiv, loadMediaData);
    }
  });

  // 文件选择
  fileInput.addEventListener('change', (e) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) {
      handleFileUpload(file, progressDiv, loadMediaData);
    }
  });

  // URL插入
  insertUrlBtn.addEventListener('click', () => {
    const url = imageUrlInput.value.trim();
    if (!url) {
      showNativeMessage('请输入图片链接', 'warning');
      return;
    }
    
    if (vditor) {
      const markdown = `![图片](${url})`;
      vditor.insertValue('\n' + markdown + '\n');
      showNativeMessage('图片链接插入成功！', 'success');
      closeModal();
    } else {
      showNativeMessage('编辑器未就绪', 'warning');
    }
  });

  // Enter键插入URL
  imageUrlInput.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
      insertUrlBtn.click();
    }
  });
}

function handleFileUpload(file: File, progressDiv: HTMLElement, refreshMediaData?: () => void) {
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    showNativeMessage('只能上传图片文件', 'error');
    return;
  }

  // 验证文件大小
  if (file.size > 2 * 1024 * 1024) {
    showNativeMessage('文件大小不能超过 2MB', 'error');
    return;
  }

  // 显示进度
  progressDiv.style.display = 'block';

  // 创建FormData
  const formData = new FormData();
  formData.append('file', file);

  // 上传文件
  fetch('/api/v1/media/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userStore.token}`
    },
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    progressDiv.style.display = 'none';
    
    if (data.code === 0 && data.data) {
      showNativeMessage('图片上传成功！', 'success');
      
      // 如果有刷新回调，刷新媒体列表
      if (refreshMediaData) {
        refreshMediaData();
        
        // 切换回浏览标签
        const modal = progressDiv.closest('#native-media-modal');
        if (modal) {
          const browseTab = modal.querySelector('#browse-tab') as HTMLElement;
          if (browseTab) {
            browseTab.click();
          }
        }
      } else {
        // 直接插入模式（兼容旧的上传逻辑）
        let imageUrl = data.data.url;
        const altText = data.data.alt_text || data.data.title || data.data.original_name || '图片';
        
        // 选择合适的尺寸
        if (data.data.variants?.variants) {
          const mdVariant = data.data.variants.variants.find((v: any) => v.label === 'md');
          const smVariant = data.data.variants.variants.find((v: any) => v.label === 'sm');
          
          if (mdVariant) {
            imageUrl = mdVariant.url;
          } else if (smVariant) {
            imageUrl = smVariant.url;
          }
        }
        
        if (vditor) {
          const markdown = `![${altText}](${imageUrl})`;
          vditor.insertValue('\n' + markdown + '\n');
          showNativeMessage('图片上传并插入成功！', 'success');
        }
      }
    } else {
      showNativeMessage('图片上传失败', 'error');
    }
  })
  .catch(error => {
    progressDiv.style.display = 'none';
    console.error('上传失败:', error);
    showNativeMessage('图片上传失败', 'error');
  });
}

function showNativeMessage(text: string, type: 'success' | 'warning' | 'error') {
  const message = document.createElement('div');
  message.style.cssText = `
    position: fixed;
    top: 50px;
    left: 50%;
    transform: translateX(-50%);
    padding: 12px 20px;
    border-radius: 4px;
    color: white;
    font-size: 14px;
    z-index: 10000;
    background: ${type === 'success' ? '#67c23a' : type === 'warning' ? '#e6a23c' : '#f56c6c'};
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  `;
  message.textContent = text;
  
  document.body.appendChild(message);
  
  setTimeout(() => {
    message.remove();
  }, 3000);
}

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
  
  // 清理全局函数
  if ((window as any).openMediaLibrary) {
    delete (window as any).openMediaLibrary;
  }
  
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
  
  // 清理粘贴事件监听器
  if (window.vditorCleanupFunctions) {
    window.vditorCleanupFunctions.forEach(cleanup => {
      try {
        cleanup();
      } catch (error) {
        console.warn('清理粘贴事件监听器失败:', error);
      }
    });
    delete window.vditorCleanupFunctions;
  }
  
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