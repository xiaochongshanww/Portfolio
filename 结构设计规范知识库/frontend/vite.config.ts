import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  base: '/static/',
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/admin': 'http://127.0.0.1:8000',
      '/ready': 'http://127.0.0.1:8000',
      '/metrics': 'http://127.0.0.1:8000',
      '/knowledge': 'http://127.0.0.1:8000',
      '/evaluation': 'http://127.0.0.1:8000',
      '/v1': 'http://127.0.0.1:8000',
      '/images': 'http://127.0.0.1:8000',
    },
  },
})
