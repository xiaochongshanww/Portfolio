<template>
  <div class="about-page">
    <!-- Hero Section -->
    <section class="hero-section py-16 px-6 relative overflow-hidden">
      <!-- 背景装饰 -->
      <div class="background-decorations">
        <div class="decoration-1"></div>
        <div class="decoration-2"></div>
        <div class="decoration-3"></div>
      </div>
      
      <div class="relative z-10 max-w-4xl mx-auto text-center">
        <!-- 个人头像 -->
        <div class="mb-8 flex justify-center">
          <div class="w-32 h-32 rounded-full border-4 border-white shadow-xl bg-gray-200 flex items-center justify-center">
            <span class="text-gray-400 text-sm">头像占位</span>
          </div>
        </div>
        
        <!-- 个人介绍 -->
        <h1 class="text-4xl md:text-5xl font-bold text-gray-800 mb-4">
          你好，我是小重山
        </h1>
        <p class="text-xl text-gray-600 mb-6 max-w-2xl mx-auto leading-relaxed">
          一名热爱技术的全栈开发者，专注于创建优雅的数字体验
        </p>
        
        <!-- 核心技能标签 -->
        <div class="hero-skills-section">
          <el-tag v-for="skill in coreSkills" :key="skill" size="large" effect="plain" class="skill-tag">
            {{ skill }}
          </el-tag>
        </div>
        
        <!-- 快速链接 -->
        <div class="hero-buttons-section">
          <el-button type="primary" size="large" round class="contact-btn">
            <el-icon class="mr-2"><User /></el-icon>
            联系我
          </el-button>
          <el-button size="large" round class="portfolio-btn">
            <el-icon class="mr-2"><TrendCharts /></el-icon>
            查看作品
          </el-button>
        </div>
      </div>
      
      <!-- 曲线分割 -->
      <div class="hero-divider">
        <svg viewBox="0 0 1200 120" preserveAspectRatio="none" class="divider-svg">
          <path d="M0,0 C300,80 600,80 1200,0 L1200,120 L0,120 Z" class="divider-path"></path>
        </svg>
      </div>
    </section>

    <!-- 主要内容区域 -->
    <div class="content-area">
      <div class="main-content-grid">
        <!-- 主要内容列 -->
        <div class="main-content">
          <!-- 个人故事 -->
          <section class="content-card">
            <div class="flex items-center mb-6">
              <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mr-4">
                <el-icon class="text-white text-xl"><User /></el-icon>
              </div>
              <h2 class="text-2xl font-bold text-gray-800">关于我</h2>
            </div>
            <div class="prose prose-gray max-w-none">
              <p class="text-gray-600 leading-relaxed mb-4">
                我是一名充满热情的全栈开发者，拥有超过5年的软件开发经验。我专注于使用现代技术栈创建高质量的Web应用程序，
                擅长前端界面设计和后端系统架构。
              </p>
              <p class="text-gray-600 leading-relaxed mb-4">
                我相信技术应该为人们的生活带来便利，因此我始终致力于开发用户友好、性能优异的应用程序。
                除了编程，我还热衷于学习新技术、分享知识，并通过这个博客平台与大家交流技术心得。
              </p>
              <p class="text-gray-600 leading-relaxed">
                当不在键盘前编程时，你可能会发现我在阅读技术书籍、探索开源项目，或者在大自然中寻找灵感。
              </p>
            </div>
          </section>

          <!-- 技能与技术栈 -->
          <section class="content-card">
            <div class="flex items-center mb-6">
              <div class="w-12 h-12 bg-gradient-to-br from-green-500 to-teal-600 rounded-xl flex items-center justify-center mr-4">
                <el-icon class="text-white text-xl"><Setting /></el-icon>
              </div>
              <h2 class="text-2xl font-bold text-gray-800">技能与技术</h2>
            </div>
            
            <div class="modern-skills-grid">
              <div v-for="category in techStack" :key="category.name" class="modern-skill-category">
                <!-- 卡片头部 -->
                <div class="skill-category-header">
                  <div class="skill-icon-wrapper">
                    <el-icon class="skill-category-icon">
                      <HomeFilled v-if="category.iconName === 'HomeFilled'" />
                      <DataAnalysis v-else-if="category.iconName === 'DataAnalysis'" />
                      <Collection v-else-if="category.iconName === 'Collection'" />
                      <Setting v-else-if="category.iconName === 'Setting'" />
                    </el-icon>
                  </div>
                  <h3 class="skill-category-title">{{ category.name }}</h3>
                </div>
                
                <!-- 技能列表 -->
                <div class="skills-list">
                  <div v-for="skill in category.skills" :key="skill.name" class="modern-skill-item">
                    <div class="skill-header">
                      <span class="skill-name">{{ skill.name }}</span>
                      <div class="skill-level-indicator" :class="getModernLevelClass(skill.label)">
                        <div class="level-dots">
                          <div v-for="i in 4" :key="i" class="level-dot" 
                               :class="{ active: i <= getLevelDots(skill.label) }"></div>
                        </div>
                        <span class="level-text">{{ skill.label }}</span>
                      </div>
                    </div>
                    
                    <!-- 现代化技能可视化 -->
                    <div class="skill-visualization">
                      <div class="skill-progress-modern" 
                           :style="{ '--skill-level': skill.level + '%' }">
                        <div class="progress-glow"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- 项目经验 -->
          <section class="content-card">
            <div class="flex items-center mb-6">
              <div class="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-600 rounded-xl flex items-center justify-center mr-4">
                <el-icon class="text-white text-xl"><EditPen /></el-icon>
              </div>
              <h2 class="text-2xl font-bold text-gray-800">项目经验</h2>
            </div>
            
            <div class="space-y-6">
              <div v-for="project in projects" :key="project.title" class="project-item group">
                <div class="project-item-layout">
                  <div class="project-icon-container">
                    <el-icon class="project-icon">
                      <EditPen v-if="project.iconName === 'EditPen'" />
                      <DataAnalysis v-else-if="project.iconName === 'DataAnalysis'" />
                      <HomeFilled v-else-if="project.iconName === 'HomeFilled'" />
                    </el-icon>
                  </div>
                  <div class="project-content">
                    <h3 class="project-title">
                      {{ project.title }}
                    </h3>
                    <p class="text-gray-600 mb-3">{{ project.description }}</p>
                    <div class="flex flex-wrap gap-2">
                      <el-tag v-for="tech in project.technologies" :key="tech" size="small" effect="plain">
                        {{ tech }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- 侧边栏 -->
        <div class="sidebar">
          <!-- 个人信息卡片 -->
          <div class="content-card">
            <h3 class="text-lg font-semibold text-gray-800 mb-4">基本信息</h3>
            <div class="space-y-3">
              <div class="flex items-center text-gray-600">
                <el-icon class="mr-3 text-blue-500"><HomeFilled /></el-icon>
                <span>中国 • 北京</span>
              </div>
              <div class="flex items-center text-gray-600">
                <el-icon class="mr-3 text-green-500"><Clock /></el-icon>
                <span>5+ 年开发经验</span>
              </div>
              <div class="flex items-center text-gray-600">
                <el-icon class="mr-3 text-purple-500"><TrendCharts /></el-icon>
                <span>全栈开发者</span>
              </div>
            </div>
          </div>

          <!-- 兴趣爱好 -->
          <div class="content-card">
            <h3 class="text-lg font-semibold text-gray-800 mb-4">兴趣爱好</h3>
            <div class="grid grid-cols-2 gap-3">
              <div v-for="interest in interests" :key="interest.name" class="interest-item">
                <div class="text-center p-3 rounded-lg bg-gray-50 hover:bg-blue-50 transition-colors">
                  <el-icon class="text-3xl text-blue-500 mb-1">
                    <Collection v-if="interest.iconName === 'Collection'" />
                    <TrendCharts v-else-if="interest.iconName === 'TrendCharts'" />
                    <InfoFilled v-else-if="interest.iconName === 'InfoFilled'" />
                    <DataBoard v-else-if="interest.iconName === 'DataBoard'" />
                  </el-icon>
                  <!-- 只显示图标，隐藏文字以实现纯图标效果 -->
                  <p class="text-xs text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity" :title="interest.name">{{ interest.name }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 联系方式 -->
          <div class="content-card">
            <h3 class="text-lg font-semibold text-gray-800 mb-4">联系我</h3>
            <div class="flex justify-center contact-links-container">
              <a v-for="contact in contacts" :key="contact.type" 
                 :href="contact.link" 
                 class="contact-link"
                 :class="getContactLinkClass(contact.type)"
                 :title="contact.label"
                 target="_blank"
                 rel="noopener noreferrer"
              >
                <!-- GitHub特殊处理，使用SVG图标 -->
                <svg v-if="contact.iconName === 'github'" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                <el-icon v-else class="text-lg">
                  <Message v-if="contact.iconName === 'Message'" />
                  <EditPen v-else-if="contact.iconName === 'EditPen'" />
                </el-icon>
              </a>
            </div>
          </div>

          <!-- 状态卡片 -->
          <div class="content-card bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200">
            <div class="text-center">
              <div class="w-16 h-16 bg-gradient-to-br from-green-500 to-teal-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <el-icon class="text-white text-2xl"><InfoFilled /></el-icon>
              </div>
              <h3 class="text-lg font-semibold text-gray-800 mb-2">当前状态</h3>
              <p class="text-gray-600 text-sm">🚀 正在开发新项目</p>
              <p class="text-gray-600 text-sm">💼 接受合作邀请</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  User, Setting, Clock, TrendCharts, InfoFilled,
  Collection, DataAnalysis, EditPen, HomeFilled, UserFilled,
  SwitchButton, DataBoard, Message
} from '@element-plus/icons-vue'

// 核心技能
const coreSkills = ref([
  'Vue.js', 'Python', 'Flask', 'JavaScript', 'Node.js', 'MySQL'
])

// 技术栈
const techStack = ref([
  {
    name: '前端开发',
    iconName: 'HomeFilled',
    skills: [
      { name: 'Vue.js', level: 90, label: '精通' },
      { name: 'JavaScript', level: 88, label: '精通' },
      { name: 'TypeScript', level: 75, label: '熟练' },
      { name: 'CSS/Tailwind', level: 85, label: '精通' }
    ]
  },
  {
    name: '后端开发', 
    iconName: 'DataAnalysis',
    skills: [
      { name: 'Python', level: 92, label: '专家' },
      { name: 'Flask', level: 88, label: '精通' },
      { name: 'Node.js', level: 75, label: '熟练' },
      { name: 'RESTful API', level: 85, label: '精通' }
    ]
  },
  {
    name: '数据库',
    iconName: 'Collection',
    skills: [
      { name: 'MySQL', level: 85, label: '精通' },
      { name: 'Redis', level: 80, label: '熟练' },
      { name: 'MongoDB', level: 70, label: '熟练' },
      { name: 'SQLAlchemy', level: 82, label: '精通' }
    ]
  },
  {
    name: '工具与部署',
    iconName: 'Setting',
    skills: [
      { name: 'Git', level: 88, label: '精通' },
      { name: 'Docker', level: 75, label: '熟练' },
      { name: 'Linux', level: 80, label: '熟练' },
      { name: 'CI/CD', level: 70, label: '熟练' }
    ]
  }
])

// 项目经验
const projects = ref([
  {
    title: '现代化博客平台',
    description: '基于 Flask 和 Vue.js 的全功能博客系统，支持文章管理、用户交互、搜索等功能',
    technologies: ['Vue.js', 'Flask', 'MySQL', 'Redis', 'Element Plus'],
    iconName: 'EditPen'
  },
  {
    title: 'RESTful API 服务',
    description: '为多个客户端应用提供统一的后端API服务，包含认证、权限管理等核心功能',
    technologies: ['Python', 'Flask', 'JWT', 'SQLAlchemy'],
    iconName: 'DataAnalysis'
  },
  {
    title: '响应式Web应用',
    description: '多个企业级Web应用的前端开发，注重用户体验和性能优化',
    technologies: ['Vue.js', 'TypeScript', 'Tailwind CSS', 'Vite'],
    iconName: 'HomeFilled'
  }
])

// 兴趣爱好 - 改为纯图标显示
const interests = ref([
  { name: '阅读', iconName: 'Collection' },
  { name: '摄影', iconName: 'TrendCharts' },
  { name: '音乐', iconName: 'InfoFilled' },
  { name: '编程', iconName: 'DataBoard' }
])

// 联系方式 - 使用SVG图标
const contacts = ref([
  {
    type: 'email',
    label: 'xiaochongshan@example.com',
    link: 'mailto:xiaochongshan@example.com',
    iconName: 'Message'
  },
  {
    type: 'github', 
    label: 'GitHub',
    link: 'https://github.com/xiaochongshanww',
    iconName: 'github' // 特殊处理，使用SVG
  },
  {
    type: 'blog',
    label: '技术博客',
    link: '/',
    iconName: 'EditPen'
  }
])

// 获取技能等级样式类
function getLevelClass(label) {
  const levelMap = {
    '专家': 'expert',
    '精通': 'proficient', 
    '熟练': 'skilled',
    '了解': 'familiar'
  }
  return levelMap[label] || 'skilled'
}

// 获取联系方式链接样式类
function getContactLinkClass(type) {
  const classMap = {
    'email': 'email-link',
    'github': 'github-link',
    'blog': 'blog-link'
  }
  return classMap[type] || 'default-link'
}

// 获取现代化技能等级样式类
function getModernLevelClass(label) {
  const levelMap = {
    '专家': 'level-expert',
    '精通': 'level-proficient', 
    '熟练': 'level-skilled',
    '了解': 'level-familiar'
  }
  return levelMap[label] || 'level-skilled'
}

// 获取技能等级点数
function getLevelDots(label) {
  const dotsMap = {
    '专家': 4,
    '精通': 3, 
    '熟练': 2,
    '了解': 1
  }
  return dotsMap[label] || 2
}

// 页面初始化
onMounted(() => {
  console.log('About页面已加载')
})
</script>

<style scoped>
.hero-section {
  min-height: 70vh;
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, 
    rgb(219 234 254) 0%, 
    rgb(196 221 253) 25%, 
    rgb(224 231 255) 50%, 
    rgb(232 229 255) 75%, 
    rgb(243 232 255) 100%);
  position: relative;
  padding-bottom: 0;
}

/* 曲线分割器 */
.hero-divider {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  overflow: hidden;
  line-height: 0;
  transform: rotate(180deg);
}

.divider-svg {
  position: relative;
  display: block;
  width: calc(100% + 1.3px);
  height: 60px;
}

.divider-path {
  fill: #ffffff;
}

/* 内容区域渐变背景 */
.content-area {
  background: linear-gradient(180deg, 
    rgb(248 250 252) 0%,
    rgb(255 255 255) 15%,
    rgb(255 255 255) 100%);
  width: 100%;
  padding: 3rem 1.5rem;
  position: relative;
  z-index: 1;
}

.content-area .main-content-grid {
  max-width: 72rem;
  margin: 0 auto;
}

.main-content-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media (min-width: 1024px) {
  .main-content-grid {
    grid-template-columns: 2fr 1fr;
  }
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.background-decorations {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0.15;
  pointer-events: none;
}

.decoration-1 {
  position: absolute;
  top: 2.5rem;
  left: 2.5rem;
  width: 5rem;
  height: 5rem;
  background-color: rgb(59 130 246);
  border-radius: 50%;
  filter: blur(20px);
  animation: pulse 3s ease-in-out infinite;
}

.decoration-2 {
  position: absolute;
  top: 5rem;
  right: 5rem;
  width: 4rem;
  height: 4rem;
  background-color: rgb(147 51 234);
  border-radius: 50%;
  filter: blur(15px);
  animation: pulse 3s ease-in-out infinite 1s;
}

.decoration-3 {
  position: absolute;
  bottom: 2.5rem;
  left: 33.333333%;
  width: 3rem;
  height: 3rem;
  background-color: rgb(99 102 241);
  border-radius: 50%;
  filter: blur(15px);
  animation: pulse 3s ease-in-out infinite 2s;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.4;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.1);
  }
}

.content-card {
  background: linear-gradient(145deg, 
    rgb(255 255 255) 0%, 
    rgb(250 251 255) 100%);
  border-radius: 1rem;
  /* 永久显示蓝色阴影，增加层次感 */
  box-shadow: 
    0 4px 6px -1px rgb(0 0 0 / 0.05), 
    0 2px 4px -2px rgb(0 0 0 / 0.03),
    0 0 0 1px rgb(59 130 246 / 0.15),
    inset 0 1px 0 rgb(255 255 255 / 0.9);
  border: none;
  padding: 1.5rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(8px);
}

/* 永久显示的顶部装饰线 */
.content-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, 
    rgb(59 130 246) 0%, 
    rgb(147 51 234) 50%,
    rgb(59 130 246) 100%);
  opacity: 0.8;
  transition: all 0.3s ease;
}

/* 增加微妙的背景纹理 */
.content-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(circle at 20% 50%, rgb(59 130 246 / 0.03) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgb(147 51 234 / 0.03) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

.content-card:hover {
  transform: translateY(-4px);
  box-shadow: 
    0 12px 32px -8px rgb(0 0 0 / 0.12), 
    0 8px 16px -8px rgb(0 0 0 / 0.08),
    0 0 0 1px rgb(59 130 246 / 0.25),
    inset 0 1px 0 rgb(255 255 255 / 1);
}

.content-card:hover::before {
  opacity: 1;
  height: 4px;
  background: linear-gradient(90deg, 
    rgb(59 130 246) 0%, 
    rgb(147 51 234) 30%,
    rgb(168 85 247) 60%,
    rgb(59 130 246) 100%);
}

.skill-tag {
  background-color: white;
  border-color: rgb(191 219 254);
  color: rgb(29 78 216);
  transition: all 0.2s ease;
}

.skill-tag:hover {
  background-color: rgb(239 246 255);
}

.contact-btn {
  background: linear-gradient(to right, rgb(59 130 246), rgb(147 51 234));
  border: none;
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  transition: all 0.3s ease;
}

.contact-btn:hover {
  background: linear-gradient(to right, rgb(37 99 235), rgb(126 34 206));
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}

.portfolio-btn {
  border: 1px solid rgb(209 213 219);
  color: rgb(55 65 81);
  transition: all 0.3s ease;
}

.portfolio-btn:hover {
  border-color: rgb(59 130 246);
  color: rgb(37 99 235);
}

.tech-category {
  background-color: rgb(249 250 251);
  border-radius: 0.5rem;
  padding: 1rem;
  transition: background-color 0.2s ease;
}

.tech-category:hover {
  background-color: rgb(243 244 246);
}

.skill-item {
  transition: all 0.3s ease;
}

.skill-item:hover {
  transform: scale(1.05);
}

/* 技能等级徽章样式 */
.skill-level-badge {
  padding: 0.125rem 0.5rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  text-align: center;
  min-width: 3rem;
}

.skill-level-badge.expert {
  background-color: rgb(220 252 231);
  color: rgb(21 128 61);
  border: 1px solid rgb(187 247 208);
}

.skill-level-badge.proficient {
  background-color: rgb(219 234 254);
  color: rgb(29 78 216);
  border: 1px solid rgb(191 219 254);
}

.skill-level-badge.skilled {
  background-color: rgb(254 240 138);
  color: rgb(146 64 14);
  border: 1px solid rgb(253 224 71);
}

.skill-level-badge.familiar {
  background-color: rgb(243 244 246);
  color: rgb(75 85 99);
  border: 1px solid rgb(209 213 219);
}

.project-item {
  padding: 1rem;
  border-radius: 0.5rem;
  transition: all 0.2s ease;
  cursor: pointer;
}

.project-item:hover {
  background-color: rgb(249 250 251);
}

.interest-item {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.interest-item:hover {
  transform: scale(1.05);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .hero-section {
    min-height: 60vh;
    padding: 3rem 1.5rem 0;
  }
  
  .divider-svg {
    height: 40px;
  }
  
  .content-area {
    padding: 2rem 1rem;
  }
  
  .content-card {
    padding: 1.25rem;
    border-radius: 0.75rem;
  }
  
  .background-decorations {
    opacity: 0.08;
  }
  
  .decoration-1, .decoration-2, .decoration-3 {
    filter: blur(10px);
  }
}

/* 确保内容在背景纹理之上 */
.content-card > *,
.content-card .el-icon,
.content-card svg {
  position: relative;
  z-index: 2;
}

.content-card > * {
  position: relative;
  z-index: 1;
}

/* 卡片标题区域增强 */
.content-card h2,
.content-card h3 {
  text-shadow: 0 1px 2px rgb(0 0 0 / 0.05);
  letter-spacing: -0.025em;
}

/* 图标容器增强 */
.content-card .w-12.h-12 {
  box-shadow: 
    0 2px 8px rgb(0 0 0 / 0.1),
    inset 0 1px 0 rgb(255 255 255 / 0.3);
  transition: all 0.3s ease;
}

.content-card:hover .w-12.h-12 {
  transform: scale(1.05);
  box-shadow: 
    0 4px 12px rgb(0 0 0 / 0.15),
    inset 0 1px 0 rgb(255 255 255 / 0.4);
}

/* 联系方式链接容器 */
.contact-links-container {
  gap: 2rem !important; /* 保持与主页博主卡片相同的间距 */
}

.contact-link {
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

.contact-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px 0 rgb(0 0 0 / 0.15);
}

/* 邮件链接特定样式 */
.email-link:hover {
  background-color: rgb(34 197 94);
  color: white;
  border-color: rgb(34 197 94);
}

/* GitHub链接特定样式 */
.github-link:hover {
  background-color: rgb(24 24 27);
  color: white;
  border-color: rgb(24 24 27);
}

/* 博客链接特定样式 */
.blog-link:hover {
  background-color: rgb(59 130 246);
  color: white;
  border-color: rgb(59 130 246);
}

/* ========== 根本性解决方案 ========== */

/* 英雄区域间距问题解决方案 */
.hero-skills-section {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 4rem !important; /* 64px 明确设置 */
}

.hero-buttons-section {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1rem;
  margin-top: 3rem !important; /* 48px 明确设置 */
  /* 总间距: 64px + 48px = 112px，视觉上充分分离 */
}

/* 项目经验卡片对齐问题解决方案 */
.project-item-layout {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 1rem;
  align-items: center; /* Grid中的居中对齐更可靠 */
}

.project-icon-container {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, rgb(219 234 254), rgb(196 181 253));
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 2;
}

.project-icon {
  color: rgb(37 99 235) !important;
  font-size: 1.25rem;
  vertical-align: middle;
}

.project-content {
  min-height: 48px; /* 确保与图标容器同高 */
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.project-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: rgb(31 41 55);
  line-height: 1.2; /* 紧凑行高确保垂直居中 */
  margin: 0;
  transition: color 0.3s ease;
}

.project-item:hover .project-title {
  color: rgb(37 99 235);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .hero-skills-section {
    margin-bottom: 2.5rem !important; /* 移动端减少间距 */
  }
  
  .hero-buttons-section {
    margin-top: 2rem !important;
  }
}

/* ========== 现代化技能卡片设计 ========== */

.modern-skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
}

.modern-skill-category {
  background: linear-gradient(145deg, 
    rgba(255, 255, 255, 0.95) 0%, 
    rgba(248, 250, 252, 0.98) 100%);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 1.25rem;
  padding: 1.75rem;
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.06),
    0 2px 8px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

/* 毛玻璃背景动效 */
.modern-skill-category::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(circle at 25% 25%, rgba(59, 130, 246, 0.05) 0%, transparent 60%),
    radial-gradient(circle at 75% 75%, rgba(147, 51, 234, 0.05) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
  opacity: 0;
  transition: opacity 0.4s ease;
}

.modern-skill-category:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.12),
    0 8px 24px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 1);
}

.modern-skill-category:hover::before {
  opacity: 1;
}

/* 卡片头部 */
.skill-category-header {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
  position: relative;
  z-index: 1;
}

.skill-icon-wrapper {
  width: 3.5rem;
  height: 3.5rem;
  background: linear-gradient(135deg, 
    rgba(59, 130, 246, 0.1) 0%, 
    rgba(147, 51, 234, 0.1) 100%);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 1rem;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.skill-icon-wrapper::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, transparent 70%);
  border-radius: 50%;
  transition: all 0.3s ease;
  transform: translate(-50%, -50%);
}

.modern-skill-category:hover .skill-icon-wrapper::after {
  width: 100%;
  height: 100%;
}

.skill-category-icon {
  font-size: 1.5rem !important;
  color: rgb(59, 130, 246);
  z-index: 1;
  position: relative;
}

.skill-category-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: rgb(15, 23, 42);
  margin: 0;
  position: relative;
  z-index: 1;
}

/* 技能列表 */
.skills-list {
  position: relative;
  z-index: 1;
}

.modern-skill-item {
  margin-bottom: 1.25rem;
  padding: 0.75rem;
  border-radius: 0.75rem;
  background: rgba(248, 250, 252, 0.5);
  border: 1px solid rgba(226, 232, 240, 0.3);
  transition: all 0.3s ease;
}

.modern-skill-item:hover {
  background: rgba(239, 246, 255, 0.8);
  border-color: rgba(59, 130, 246, 0.2);
  transform: translateX(4px);
}

.skill-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.skill-name {
  font-weight: 500;
  color: rgb(51, 65, 85);
  font-size: 0.95rem;
}

/* 现代化等级指示器 */
.skill-level-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.level-dots {
  display: flex;
  gap: 0.25rem;
}

.level-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.3);
  transition: all 0.3s ease;
}

.level-dot.active {
  background: linear-gradient(45deg, rgb(59, 130, 246), rgb(147, 51, 234));
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.4);
}

.level-text {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.125rem 0.5rem;
  border-radius: 0.375rem;
}

.level-expert .level-text {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(16, 185, 129, 0.1));
  color: rgb(21, 128, 61);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.level-proficient .level-text {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(37, 99, 235, 0.1));
  color: rgb(29, 78, 216);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.level-skilled .level-text {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(217, 119, 6, 0.1));
  color: rgb(146, 64, 14);
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.level-familiar .level-text {
  background: linear-gradient(135deg, rgba(156, 163, 175, 0.1), rgba(107, 114, 128, 0.1));
  color: rgb(75, 85, 99);
  border: 1px solid rgba(156, 163, 175, 0.2);
}

/* 现代化进度可视化 */
.skill-visualization {
  position: relative;
  height: 6px;
  background: linear-gradient(90deg, 
    rgba(226, 232, 240, 0.5) 0%, 
    rgba(203, 213, 225, 0.3) 100%);
  border-radius: 3px;
  overflow: hidden;
}

.skill-progress-modern {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: var(--skill-level);
  background: linear-gradient(90deg, 
    rgba(59, 130, 246, 0.8) 0%, 
    rgba(147, 51, 234, 0.9) 50%,
    rgba(168, 85, 247, 1) 100%);
  border-radius: 3px;
  transition: all 1.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.progress-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(255, 255, 255, 0.4) 50%, 
    transparent 100%);
  animation: progressShimmer 2s infinite;
}

@keyframes progressShimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

/* 响应式优化 */
@media (max-width: 768px) {
  .modern-skills-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .modern-skill-category {
    padding: 1.25rem;
  }
  
  .skill-icon-wrapper {
    width: 3rem;
    height: 3rem;
  }
  
  .skill-category-icon {
    font-size: 1.25rem !important;
  }
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(to bottom, #3b82f6, #8b5cf6);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(to bottom, #2563eb, #7c3aed);
}
</style>