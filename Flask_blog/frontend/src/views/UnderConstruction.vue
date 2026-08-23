<template>
  <div class="shell under-construction">
    <div class="uc-inner">
      <span class="uc-tag">{{ title }}</span>
      <h1>这个页面正在建设中</h1>
      <p>该模块属于后续阶段交付,当前先返回首页继续阅读。</p>
      <a href="/" class="uc-home" @click.prevent="$router.push('/')">← 返回首页</a>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UnderConstruction',
  props: {
    title: { type: String, default: '规划中' },
  },
}
</script>

<style scoped>
.under-construction {
  padding-top: 90px;
  padding-bottom: 110px;
}
.uc-inner {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--surface);
  padding: 46px 40px;
  text-align: center;
}
.uc-tag {
  display: inline-block;
  font-size: 11px;
  color: var(--signal-ink);
  background: var(--signal-soft);
  border-radius: 999px;
  padding: 4px 12px;
  margin-bottom: 16px;
}
h1 {
  font-size: 28px;
  letter-spacing: -0.03em;
  margin: 0 0 10px;
}
p {
  color: var(--muted);
  font-size: 14px;
  margin: 0 0 22px;
}
.uc-home {
  display: inline-flex;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  border-bottom: 2px solid var(--signal);
  padding-bottom: 2px;
}
</style>
