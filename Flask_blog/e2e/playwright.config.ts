import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.ts',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
  },
  webServer: [
    {
      command: 'cd backend && python run.py',
      port: 5000,
      timeout: 10000,
      reuseExistingServer: true,
    },
    {
      command: 'cd frontend && npx vite --port 5173',
      port: 5173,
      timeout: 10000,
      reuseExistingServer: true,
    },
  ],
})
