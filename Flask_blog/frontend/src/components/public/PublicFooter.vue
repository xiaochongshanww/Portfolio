<template>
  <footer class="site-footer">
    <div class="shell footer-inner">
      <div>© {{ year }} 小重山</div>
      <div class="footer-links">
        <a href="https://github.com/xiaochongshanww" target="_blank" rel="noopener noreferrer">GitHub</a>
        <a href="/about">关于</a>
      </div>
    </div>
  </footer>
</template>

<script>
/**
 * 公开站 Footer(01 号规范第 4 节):单行轻量,无站点地图。
 * RSS 链接待后端提供 feed 后补入。
 */
export default {
  name: 'PublicFooter',
  computed: {
    year() {
      return new Date().getFullYear()
    },
  },
}
</script>

<style scoped>
.site-footer {
  border-top: 1px solid var(--line);
  padding: 25px 0 32px;
}
.footer-inner {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  color: var(--muted);
  font-size: 13px;
}
.footer-links {
  display: flex;
  gap: 18px;
}
.footer-links a:hover {
  color: var(--text);
}
</style>
