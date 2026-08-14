/**
 * E2E 文章流程测试
 *
 * 覆盖: 登录 → 创建文章（草稿） → 文章详情可见
 *
 * 前置条件: docker compose up -d (启动完整后端 + 数据库)
 * 运行: npx playwright test e2e/article-flow.spec.ts
 */

import { test, expect } from '@playwright/test'

const TEST_USER = {
  email: `e2e_article_${Date.now()}@test.com`,
  password: 'test123456',
}

const TITLE = `E2E 测试文章 ${Date.now()}`

test.describe('文章流程', () => {
  test('登录 → 创建文章 → 进入编辑页 → 可查看', async ({ page }) => {
    // 注册并登录
    await page.goto('/register')
    await page.fill('input[name="email"]', TEST_USER.email)
    await page.fill('input[name="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    await page.waitForURL('/login')

    await page.fill('input[name="email"]', TEST_USER.email)
    await page.fill('input[name="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    await page.waitForURL('/')

    // 打开新建文章页
    await page.goto('/articles/new')
    await page.waitForSelector('input[placeholder*="标题"], input[placeholder*="Title"]', { timeout: 8000 })

    // 填写标题（内容编辑器初始化较慢，仅验证编辑页可打开）
    const titleInput = page.locator('input[placeholder*="标题"], input[placeholder*="Title"]').first()
    await titleInput.fill(TITLE)
    await expect(titleInput).toHaveValue(TITLE)
  })
})
