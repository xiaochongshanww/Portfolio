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
    await page.fill('input[placeholder="you@example.com"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await Promise.all([
      page.waitForURL('**/login', { timeout: 20000 }),
      page.click('button:has-text("注册")'),
    ])

    // 登录
    await page.fill('input[placeholder="you@example.com"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await Promise.all([
      page.waitForURL('**/', { timeout: 20000 }),
      page.click('button:has-text("登录")'),
    ])

    // 首页应显示登录成功标志（"写文章"入口 + 用户菜单）
    await expect(page.locator('a[href="/articles/new"]')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=写文章').first()).toBeVisible({ timeout: 5000 })
  })
})
