<template>
  <Teleport to="body">
    <div class="read-progress-track" aria-hidden="true">
      <div class="read-progress-bar" :style="{ width: progress + '%' }" />
    </div>
  </Teleport>
</template>

<script>
import { useReadingProgress } from '../../composables/useReadingProgress'

export default {
  name: 'ReadingProgressBar',
  setup() {
    const { progress } = useReadingProgress()
    return { progress }
  },
}
</script>

<style scoped>
/* 03 号规范第 22 节:页面顶部 2px 进度条,signal 色 */
.read-progress-track {
  position: fixed;
  left: 0;
  top: 0;
  height: 2px;
  width: 100%;
  z-index: 200;
  pointer-events: none;
}
.read-progress-bar {
  height: 100%;
  background: var(--signal);
}
</style>
