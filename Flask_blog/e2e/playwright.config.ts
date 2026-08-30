import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.ts',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
    },
  },
  webServer: [
    {
      command: process.env.PYTHON_BIN || 'python',
      args: ['run.py'],
      cwd: 'backend',
      port: 5050,
      timeout: 15000,
      reuseExistingServer: true,
    },
    {
      command: 'npx vite --port 5173',
      cwd: 'frontend',
      port: 5173,
      timeout: 15000,
      reuseExistingServer: true,
    },
  ],
})
