import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig(({ command }) => ({
  plugins: [
    vue(),
    tailwindcss(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      // dts 仅在 dev server 写入:build 与 dev 并发运行时会争抢文件句柄(Windows 下报 UNKNOWN)
      dts: command === 'serve' ? 'src/auto-imports.d.ts' : false
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: command === 'serve' ? 'src/components.d.ts' : false
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    minify: 'esbuild',
    esbuild: {
      drop: process.env.NODE_ENV === 'production' ? ['console'] : [],
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          element: ['element-plus'],
          highlight: ['highlight.js'],
          axios: ['axios']
        }
      }
    },
    chunkSizeWarningLimit: 1200
  },
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5050',
        changeOrigin: true
      },
      '/public': {
        target: 'http://127.0.0.1:5050',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://127.0.0.1:5050',
        changeOrigin: true
      }
    }
  }
}));