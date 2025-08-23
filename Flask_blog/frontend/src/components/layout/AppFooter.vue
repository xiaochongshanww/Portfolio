<template>
  <footer class="modern-footer">
    <div class="footer-container">
      <!-- 装饰性背景元素 -->
      <div class="footer-decoration"></div>
      <div class="footer-pattern"></div>
      
      <!-- 主要内容区域 -->
      <div class="footer-content">
        <div class="footer-main">
          <!-- Logo 和介绍 -->
          <div class="footer-brand">
            <div class="brand-logo">
              <el-icon size="28"><EditPen /></el-icon>
            </div>
            <h3 class="brand-title">小重山的博客</h3>
            <p class="brand-description">一个专注于技术分享和生活感悟的个人博客</p>
          </div>
          
          <!-- 快速链接 -->
          <div class="footer-links">
            <div class="links-section">
              <h4 class="links-title">快速导航</h4>
              <ul class="links-list">
                <li><router-link to="/" class="footer-link">首页</router-link></li>
                <li><router-link to="/archive" class="footer-link">文章归档</router-link></li>
                <li><router-link to="/categories" class="footer-link">分类浏览</router-link></li>
                <li><router-link to="/tags" class="footer-link">标签云</router-link></li>
              </ul>
            </div>
            
            <div class="links-section">
              <h4 class="links-title">关于</h4>
              <ul class="links-list">
                <li><router-link to="/about" class="footer-link">关于我们</router-link></li>
                <li><a href="#" class="footer-link">联系方式</a></li>
                <li><a href="#" class="footer-link">隐私政策</a></li>
                <li><a href="#" class="footer-link">使用条款</a></li>
              </ul>
            </div>
          </div>
          
          <!-- 社交媒体链接 -->
          <div class="footer-social">
            <h4 class="social-title">关注我们</h4>
            <div class="social-links">
              <a href="#" class="social-link" title="GitHub">
                <el-icon size="20"><Link /></el-icon>
              </a>
              <a href="#" class="social-link" title="微博">
                <el-icon size="20"><ChatDotRound /></el-icon>
              </a>
              <a href="#" class="social-link" title="邮箱">
                <el-icon size="20"><Message /></el-icon>
              </a>
              <a href="#" class="social-link" title="RSS">
                <el-icon size="20"><Connection /></el-icon>
              </a>
            </div>
          </div>
        </div>
        
        <!-- 底部版权信息 -->
        <div class="footer-bottom">
          <div class="footer-divider"></div>
          <div class="footer-copyright">
            <div class="copyright-text">
              <p>&copy; 2025 <span class="highlight">小重山的博客</span>. All rights reserved.</p>
              <p class="powered-by">Powered by <span class="tech-stack">Vue 3</span> & <span class="tech-stack">Flask</span></p>
            </div>
            <div class="footer-stats">
              <span class="stat-item">
                <el-icon size="14"><View /></el-icon>
                今日访问: {{ todayViews }}
              </span>
              <span class="stat-item">
                <el-icon size="14"><User /></el-icon>
                总访客: {{ totalVisitors }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { EditPen, Link, ChatDotRound, Message, Connection, View, User } from '@element-plus/icons-vue'

// 统计数据
const todayViews = ref(1247)
const totalVisitors = ref(15632)

// 模拟获取统计数据
const fetchStats = async () => {
  // 这里可以调用 API 获取真实数据
  // const response = await apiClient.get('/stats/visitors')
  // todayViews.value = response.data.today
  // totalVisitors.value = response.data.total
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
/* ===== 现代化页脚样式 ===== */
.modern-footer {
  position: relative;
  background: 
    radial-gradient(circle at 20% 80%, rgba(59, 130, 246, 0.05) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.05) 0%, transparent 50%),
    radial-gradient(circle at 40% 40%, rgba(6, 182, 212, 0.05) 0%, transparent 50%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
  border-top: 1px solid rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(20px);
  margin-top: 4rem;
  overflow: hidden;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 3rem 2rem 1.5rem;
  position: relative;
  z-index: 2;
}

/* 装饰性背景元素 */
.footer-decoration {
  position: absolute;
  top: -100px;
  left: -100px;
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.05));
  border-radius: 50%;
  filter: blur(40px);
  animation: float-decoration 8s ease-in-out infinite;
}

.footer-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 2px 2px, rgba(59, 130, 246, 0.15) 1px, transparent 0);
  background-size: 40px 40px;
  opacity: 0.3;
  pointer-events: none;
}

@keyframes float-decoration {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(180deg); }
}

.footer-content {
  position: relative;
  z-index: 3;
}

.footer-main {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 3rem;
  margin-bottom: 2.5rem;
}

/* 品牌区域 */
.footer-brand {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.brand-logo {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 1rem;
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.25);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.brand-logo::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.2) 50%, transparent 60%);
  transform: rotate(45deg) translateX(-100%);
  transition: transform 0.6s ease;
}

.brand-logo:hover {
  transform: scale(1.05) rotate(-2deg);
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.3);
}

.brand-logo:hover::before {
  transform: rotate(45deg) translateX(100%);
}

.brand-title {
  font-size: 1.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.75rem;
  letter-spacing: -0.025em;
}

.brand-description {
  color: #64748b;
  font-size: 0.875rem;
  line-height: 1.6;
  max-width: 250px;
}

/* 链接区域 */
.footer-links {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.links-section {
  display: flex;
  flex-direction: column;
}

.links-title {
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 1rem;
  position: relative;
}

.links-title::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 30px;
  height: 2px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  border-radius: 1px;
}

.links-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.links-list li {
  margin-bottom: 0.5rem;
}

.footer-link {
  color: #64748b;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0;
  position: relative;
}

.footer-link::before {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 0;
  height: 1px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  transition: width 0.3s ease;
}

.footer-link:hover {
  color: #3b82f6;
  transform: translateX(4px);
}

.footer-link:hover::before {
  width: 100%;
}

/* 社交媒体区域 */
.footer-social {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.social-title {
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 1rem;
}

.social-links {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.social-link {
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  text-decoration: none;
  transition: all 0.3s ease;
  backdrop-filter: blur(8px);
  position: relative;
  overflow: hidden;
}

.social-link::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.social-link:hover {
  transform: translateY(-2px) scale(1.05);
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15);
}

.social-link:hover::before {
  opacity: 1;
}

.social-link:hover .el-icon {
  color: white;
  position: relative;
  z-index: 2;
}

/* 底部版权区域 */
.footer-bottom {
  margin-top: 2rem;
}

.footer-divider {
  height: 1px;
  background: linear-gradient(
    90deg, 
    transparent 0%, 
    rgba(59, 130, 246, 0.2) 25%, 
    rgba(139, 92, 246, 0.2) 75%, 
    transparent 100%
  );
  margin-bottom: 1.5rem;
}

.footer-copyright {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.copyright-text p {
  margin: 0 0 0.25rem 0;
  font-size: 0.875rem;
  color: #64748b;
}

.highlight {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 600;
}

.powered-by {
  font-size: 0.75rem;
  opacity: 0.8;
}

.tech-stack {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.7rem;
}

.footer-stats {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: #64748b;
  background: rgba(59, 130, 246, 0.05);
  padding: 0.375rem 0.75rem;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.1);
  transition: all 0.3s ease;
}

.stat-item:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.2);
  transform: scale(1.02);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .footer-container {
    padding: 2rem 1rem 1rem;
  }
  
  .footer-main {
    grid-template-columns: 1fr;
    gap: 2rem;
    text-align: center;
  }
  
  .footer-brand {
    align-items: center;
  }
  
  .footer-social {
    align-items: center;
  }
  
  .footer-links {
    grid-template-columns: 1fr 1fr;
  }
  
  .footer-copyright {
    flex-direction: column;
    text-align: center;
  }
  
  .footer-stats {
    flex-wrap: wrap;
    justify-content: center;
  }
}

@media (max-width: 640px) {
  .footer-links {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  
  .social-links {
    justify-content: center;
  }
  
  .brand-description {
    max-width: 100%;
    text-align: center;
  }
}
</style>
