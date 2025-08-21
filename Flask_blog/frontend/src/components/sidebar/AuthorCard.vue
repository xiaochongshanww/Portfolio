<template>
  <div class="author-card" style="background-color: rgb(248 250 252); border-radius: 24px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: all 0.3s ease; margin-bottom: 16px;">
    <div class="text-center">
      <!-- 头像 -->
      <div style="width: 100px; height: 100px; margin: 0 auto 16px auto; border-radius: 50%; overflow: hidden; background: linear-gradient(to bottom right, rgb(96 165 250), rgb(168 85 247)); padding: 2px;">
        <div style="width: 100%; height: 100%; border-radius: 50%; background: white; display: flex; align-items: center; justify-content: center;">
          <img 
            v-if="authorAvatar && !avatarError" 
            :src="authorAvatar" 
            alt="博主头像" 
            style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;"
            @error="handleAvatarError"
          />
          <div v-else style="width: 24px; height: 24px; border-radius: 50%; background: linear-gradient(to bottom right, rgb(59 130 246), rgb(147 51 234)); display: flex; align-items: center; justify-content: center;">
            <el-icon size="14" style="color: white;"><User /></el-icon>
          </div>
        </div>
      </div>
      
      <!-- 标题 -->
      <h3 class="text-lg font-semibold text-gray-900 mb-2">小重山</h3>
      
      <!-- 描述 -->
      <p class="text-gray-600 text-sm leading-relaxed mb-4">
        分享前端技术、后端开发、人工智能等领域的见解和经验
      </p>
      
      <!-- 社交链接 -->
      <div class="flex justify-center social-links-container">
        <a 
          href="https://github.com/xiaochongshanww" 
          target="_blank"
          rel="noopener noreferrer"
          class="social-link github-link"
          title="GitHub"
        >
          <!-- GitHub SVG 图标 -->
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
          </svg>
        </a>
        <a 
          href="#" 
          class="social-link wechat-link"
          title="微信公众号"
          @click.prevent="showWechatQR"
        >
          <!-- 微信 SVG 图标 -->
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.162 4.203 2.969 5.543.32.237.354.66.159 1.004-.301.53-.629 1.063-.629 1.063s-.013.045.013.045c.045 0 .154-.045.199-.067.793-.354 1.857-.816 2.248-.955.08-.028.154-.028.235-.011.328.045.69.068 1.058.068.045 0 .09 0 .135-.003C6.175 14.866 6 13.417 6 11.883c0-4.354 3.891-7.878 8.691-7.878 1.96 0 3.77.656 5.164 1.746-.682-3.234-3.937-5.563-7.864-5.563zM3.738 7.531c.679 0 1.229.55 1.229 1.229s-.55 1.229-1.229 1.229-1.229-.55-1.229-1.229.55-1.229 1.229-1.229zm5.715 0c.679 0 1.229.55 1.229 1.229s-.55 1.229-1.229 1.229-1.229-.55-1.229-1.229.55-1.229 1.229-1.229z"/>
            <path d="M23.922 11.883c0-3.712-3.366-6.721-7.518-6.721s-7.518 3.009-7.518 6.721 3.366 6.721 7.518 6.721c.301 0 .602-.022.896-.067.079-.011.158-.011.237.011.346.122 1.229.534 1.908.846.034.022.135.056.169.056.022 0 .011-.034.011-.034s-.281-.479-.558-.934c-.169-.281-.135-.646.113-.858 1.579-1.167 2.607-2.879 2.607-4.741zM13.655 10.18c-.567 0-1.027.46-1.027 1.027s.46 1.027 1.027 1.027 1.027-.46 1.027-1.027-.46-1.027-1.027-1.027zm5.188 0c-.567 0-1.027.46-1.027 1.027s.46 1.027 1.027 1.027 1.027-.46 1.027-1.027-.46-1.027-1.027-1.027z"/>
          </svg>
        </a>
      </div>
      
      <!-- 微信二维码弹窗 -->
      <el-dialog 
        v-model="showWechatDialog" 
        title="微信公众号" 
        width="90%"
        :style="{ maxWidth: '400px', minWidth: '320px' }"
        center
        :show-close="true"
        :z-index="3000"
        append-to-body
      >
        <div class="text-center">
          <!-- 二维码区域 -->
          <div class="mb-4">
            <!-- 当二维码图片可用时显示 -->
            <div v-if="!qrError && qrImageSrc" class="qr-container">
              <img 
                :src="qrImageSrc" 
                alt="微信公众号二维码" 
                class="qr-image"
                @error="handleQRError"
                @load="handleQRLoad"
              />
            </div>
            
            <!-- 二维码加载失败时的备用方案 -->
            <div v-else class="qr-fallback">
              <div class="w-48 h-48 mx-auto border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 flex flex-col items-center justify-center">
                <!-- 微信图标 -->
                <svg width="48" height="48" viewBox="0 0 24 24" fill="#22c55e" class="mb-3">
                  <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.162 4.203 2.969 5.543.32.237.354.66.159 1.004-.301.53-.629 1.063-.629 1.063s-.013.045.013.045c.045 0 .154-.045.199-.067.793-.354 1.857-.816 2.248-.955.08-.028.154-.028.235-.011.328.045.69.068 1.058.068.045 0 .09 0 .135-.003C6.175 14.866 6 13.417 6 11.883c0-4.354 3.891-7.878 8.691-7.878 1.96 0 3.77.656 5.164 1.746-.682-3.234-3.937-5.563-7.864-5.563zM3.738 7.531c.679 0 1.229.55 1.229 1.229s-.55 1.229-1.229 1.229-1.229-.55-1.229-1.229.55-1.229 1.229-1.229zm5.715 0c.679 0 1.229.55 1.229 1.229s-.55 1.229-1.229 1.229-1.229-.55-1.229-1.229.55-1.229 1.229-1.229z"/>
                  <path d="M23.922 11.883c0-3.712-3.366-6.721-7.518-6.721s-7.518 3.009-7.518 6.721 3.366 6.721 7.518 6.721c.301 0 .602-.022.896-.067.079-.011.158-.011.237.011.346.122 1.229.534 1.908.846.034.022.135.056.169.056.022 0 .011-.034.011-.034s-.281-.479-.558-.934c-.169-.281-.135-.646.113-.858 1.579-1.167 2.607-2.879 2.607-4.741zM13.655 10.18c-.567 0-1.027.46-1.027 1.027s.46 1.027 1.027 1.027 1.027-.46 1.027-1.027-.46-1.027-1.027-1.027zm5.188 0c-.567 0-1.027.46-1.027 1.027s.46 1.027 1.027 1.027 1.027-.46 1.027-1.027-.46-1.027-1.027-1.027z"/>
                </svg>
                <p class="text-gray-500 text-sm">二维码暂不可用</p>
                <p class="text-gray-400 text-xs mt-1">请直接搜索公众号</p>
              </div>
            </div>
          </div>
          
          <!-- 文字信息 -->
          <div class="space-y-2">
            <p class="text-gray-600 text-sm">
              {{ qrError ? '请在微信中搜索公众号' : '扫描二维码关注公众号' }}
            </p>
            <p class="text-gray-800 font-medium">小重山的学习笔记</p>
            <p v-if="qrError" class="text-blue-600 text-sm mt-3 px-3 py-2 bg-blue-50 rounded-lg">
              微信号：xiaochongshan_tech
            </p>
          </div>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { User } from '@element-plus/icons-vue'

// 头像管理
const authorAvatar = ref(null)
const avatarError = ref(false)

// 微信二维码弹窗
const showWechatDialog = ref(false)
const qrError = ref(false)
const qrImageSrc = ref(null)

// 二维码图片备选方案
const qrImageSources = [
  '/assets/images/wechat-qr.png',
  '/assets/images/wechat-qr.jpg', 
  '/assets/wechat-qr.png',
  '/uploads/wechat-qr.png',
  null // 最后使用备用方案
]
let currentQRIndex = 0

// 头像备选方案
const avatarSources = [
  '/assets/author-avatar.jpg',
  '/assets/author-avatar.png', 
  '/uploads/author-avatar.jpg',
  '/assets/default-avatar.svg',
  'https://api.dicebear.com/7.x/avataaars/svg?seed=blog-author&backgroundColor=random',
  null // 最后使用默认图标
]

let currentAvatarIndex = 0

function handleAvatarError() {
  avatarError.value = true
  currentAvatarIndex++
  tryLoadNextAvatar()
}

function tryLoadNextAvatar() {
  if (currentAvatarIndex < avatarSources.length - 1) {
    const nextAvatar = avatarSources[currentAvatarIndex]
    if (nextAvatar) {
      avatarError.value = false
      authorAvatar.value = nextAvatar
    } else {
      authorAvatar.value = null
    }
  } else {
    authorAvatar.value = null
  }
}

function initializeAvatar() {
  // 从安全的本地 SVG 头像开始
  currentAvatarIndex = 3
  avatarError.value = false
  authorAvatar.value = avatarSources[currentAvatarIndex]
}

// 微信二维码相关函数
function showWechatQR() {
  // 每次打开弹窗时尝试加载二维码
  initializeQRCode()
  showWechatDialog.value = true
}

function handleQRError() {
  console.log('二维码图片加载失败，尝试下一个备选方案')
  currentQRIndex++
  tryLoadNextQRImage()
}

function handleQRLoad() {
  console.log('二维码图片加载成功')
  qrError.value = false
}

function tryLoadNextQRImage() {
  if (currentQRIndex < qrImageSources.length - 1) {
    const nextQRSource = qrImageSources[currentQRIndex]
    if (nextQRSource) {
      qrImageSrc.value = nextQRSource
    } else {
      // 所有图片源都失败，显示备用方案
      qrError.value = true
      qrImageSrc.value = null
    }
  } else {
    // 所有备选方案都用完了，显示备用界面
    qrError.value = true
    qrImageSrc.value = null
  }
}

function initializeQRCode() {
  // 重置状态并开始尝试加载第一个二维码图片
  currentQRIndex = 0
  qrError.value = false
  qrImageSrc.value = qrImageSources[currentQRIndex]
}

onMounted(() => {
  initializeAvatar()
})
</script>

<style scoped>

/* 社交链接容器间距 */
.social-links-container {
  gap: 2rem !important; /* 32px 间距，使用 !important 确保生效 */
}

.social-link {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 12px;
  background-color: rgb(248 250 252);
  border: 1px solid rgb(226 232 240);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgb(71 85 105);
  text-decoration: none;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
}

.social-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px 0 rgb(0 0 0 / 0.15);
}

/* GitHub 特定样式 */
.github-link:hover {
  background-color: rgb(24 24 27);
  color: white;
  border-color: rgb(24 24 27);
}

/* 微信特定样式 */
.wechat-link:hover {
  background-color: rgb(34 197 94);
  color: white;
  border-color: rgb(34 197 94);
}

/* 头像容错样式 */
.avatar-fallback {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 二维码图片容器和尺寸限制 */
.qr-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  max-width: 240px;
  margin: 0 auto;
  padding: 8px;
  border: 1px solid rgb(229 231 235);
  border-radius: 12px;
  background-color: rgb(249 250 251);
}

.qr-image {
  max-width: 100%;
  max-height: 224px; /* 240px - 16px padding */
  width: auto;
  height: auto;
  object-fit: contain; /* 保持宽高比，完整显示图片 */
  border-radius: 8px;
  box-shadow: 0 2px 4px 0 rgb(0 0 0 / 0.1);
}

/* 确保微信二维码弹窗在最高层级 */
:deep(.el-dialog__wrapper) {
  z-index: 3000 !important;
}

:deep(.el-overlay) {
  z-index: 3000 !important;
}

:deep(.el-dialog) {
  z-index: 3001 !important;
}
</style>