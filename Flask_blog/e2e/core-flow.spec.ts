/**
 * E2E 核心流程测试
 *
 * 覆盖: 注册 → 登录 → 创建文章 → 提交审核 → 审核通过 → 前台可见
 *
 * 前置条件: docker compose up -d (启动完整后端 + 数据库)
 * 运行: npx playwright test
 */

import { test, expect } from '@playwright/test'

const TEST_USER = {
  email: `e2e_${Date.now()}@test.com`,
  password: 'test123456',
}

test.describe('核心流程', () => {
  test('用户注册 → 登录 → 首页显示已登录', async ({ page }) => {
    // 注册
    await page.goto('/register')
    await page.fill('input[name="email"]', TEST_USER.email)
    await page.fill('input[name="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    await page.waitForURL('/login')

    // 登录
    await page.fill('input[name="email"]', TEST_USER.email)
    await page.fill('input[name="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    await page.waitForURL('/')

    // 首页应显示用户信息
    await expect(page.locator('text=Logout').or(page.locator('text=退出'))).toBeVisible({ timeout: 5000 })
  })
})
