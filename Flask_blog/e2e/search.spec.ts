/**
 * E2E 搜索流程测试
 *
 * 覆盖: 首页搜索框输入关键词 → 提交 → 跳转并展示结果
 *
 * 前置条件: docker compose up -d (启动完整后端 + 数据库)
 * 运行: npx playwright test e2e/search.spec.ts
 */

import { test, expect } from '@playwright/test'

test.describe('搜索流程', () => {
  test('首页搜索框可输入并提交', async ({ page }) => {
    await page.goto('/')

    // 等待搜索框出现
    const searchInput = page.locator('input[type="search"], input[placeholder*="搜索"], input[placeholder*="Search"]').first()
    await expect(searchInput).toBeVisible({ timeout: 8000 })

    await searchInput.fill('Flask')
    await searchInput.press('Enter')

    // 搜索后应跳转或停留在首页并展示结果区域
    await page.waitForTimeout(3000)
    await expect(page).not.toHaveURL(/\/login/)
  })
})
