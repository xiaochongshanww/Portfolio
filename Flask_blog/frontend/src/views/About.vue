<template>
  <div class="about-page">
    <div class="max-w-4xl mx-auto py-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-8">关于我们</h1>
      <div class="prose prose-lg max-w-none">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          <h2 class="text-2xl font-semibold text-gray-900 mb-4">欢迎来到我们的博客平台</h2>
          <p class="text-gray-600 mb-6">
            这是一个基于 Flask 和 Vue.js 构建的现代化博客平台，致力于为用户提供优质的内容创作和阅读体验。
          </p>
          
          <h3 class="text-xl font-semibold text-gray-900 mb-3">平台特色</h3>
          <ul class="list-disc list-inside text-gray-600 mb-6 space-y-2">
            <li>响应式设计，支持多终端访问</li>
            <li>强大的文章编辑器，支持 Markdown 语法</li>
            <li>完善的分类和标签系统</li>
            <li>用户互动功能（点赞、收藏、评论）</li>
            <li>后台管理系统，便于内容管理</li>
            <li>搜索功能，快速找到感兴趣的内容</li>
          </ul>
          
          <h3 class="text-xl font-semibold text-gray-900 mb-3">技术栈</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <h4 class="font-medium text-gray-900 mb-2">前端技术</h4>
              <ul class="text-gray-600 space-y-1">
                <li>• Vue.js 3</li>
                <li>• Element Plus</li>
                <li>• Tailwind CSS</li>
                <li>• Vite</li>
              </ul>
            </div>
            <div>
              <h4 class="font-medium text-gray-900 mb-2">后端技术</h4>
              <ul class="text-gray-600 space-y-1">
                <li>• Flask</li>
                <li>• SQLAlchemy</li>
                <li>• Redis</li>
                <li>• JWT认证</li>
              </ul>
            </div>
          </div>
          
          <h3 class="text-xl font-semibold text-gray-900 mb-3">联系我们</h3>
          <p class="text-gray-600">
            如果您有任何问题或建议，欢迎通过以下方式联系我们：
          </p>
          <div class="mt-4 space-y-2 text-gray-600">
            <p>📧 邮箱: admin@example.com</p>
            <p>🌐 网站: https://example.com</p>
            <p>📱 微信: blogplatform</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 静态页面，无需额外逻辑
</script>

<style scoped>
.prose {
  line-height: 1.7;
}
</style>