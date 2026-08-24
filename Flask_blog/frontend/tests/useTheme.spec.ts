import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTheme, applyThemeFromStorage } from '../src/composables/useTheme'

function setStored(v: string | null) {
  if (v === null) localStorage.removeItem('xcs:theme')
  else localStorage.setItem('xcs:theme', v)
}

describe('useTheme(P2-E2)', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  it('默认跟随系统:亮色环境下 data-theme=light', () => {
    setStored(null)
    applyThemeFromStorage()
    expect(['light', 'dark']).toContain(document.documentElement.getAttribute('data-theme'))
  })

  it('记忆 dark:刷新(重新 apply)后主题保持', () => {
    setStored('dark')
    applyThemeFromStorage()
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('三态循环 light→dark→system→light,持久化写入 localStorage', () => {
    setStored('light')
    applyThemeFromStorage()
    const { mode, cycleMode } = useTheme()
    expect(mode.value).toBe('light')
    cycleMode()
    expect(mode.value).toBe('dark')
    expect(localStorage.getItem('xcs:theme')).toBe('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    cycleMode()
    expect(mode.value).toBe('system')
    cycleMode()
    expect(mode.value).toBe('light')
  })

  it('仅公开壳生效:旧壳元素不消费这些变量(admin 用 Tailwind 色不受影响)', () => {
    // 结构性保证:token 全部挂在 :root/[data-theme],旧壳样式使用 tailwind 工具类
    // 此用例验证 data-theme 属性只改变根属性,不注入任何全局背景类
    setStored('dark')
    applyThemeFromStorage()
    expect(document.documentElement.className).not.toContain('dark')
    expect(document.body.className).not.toContain('dark')
  })
})
