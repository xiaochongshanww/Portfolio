import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './vitest.setup.ts',
    coverage: {
      provider: 'v8',
      enabled: false,
      include: ['src/stores/', 'src/views/Login.vue', 'src/components/ArticleContentRenderer.vue'],
      thresholds: {
        lines: 20,
        statements: 20,
      },
    },
  },
});
