/**
 * 公开站主题管理(P2-E2):亮/暗/跟随系统 三态。
 * - localStorage 记忆(xcs:theme),默认跟随系统;
 * - 仅公开壳消费 token([data-theme] 只影响 CSS 变量,旧壳用 Tailwind 色不受影响);
 * - 防 FOUC:main.js 挂载前调用 applyThemeFromStorage()。
 */
import { ref, computed } from 'vue'

const STORAGE_KEY = 'xcs:theme'

/** @typedef {'light'|'dark'|'system'} ThemeMode */

/** @type {import('vue').Ref<ThemeMode>} */
const mode = ref(readStored())

/** @returns {ThemeMode} */
function readStored() {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'light' || v === 'dark' || v === 'system') return v
  } catch (e) { /* ignore */ }
  return 'system'
}

function systemPrefersDark() {
  return typeof matchMedia !== 'undefined' && matchMedia('(prefers-color-scheme: dark)').matches
}

/** 实际生效主题 */
const applied = computed(() =>
  mode.value === 'system' ? (systemPrefersDark() ? 'dark' : 'light') : mode.value,
)

function persistAndApply() {
  try {
    localStorage.setItem(STORAGE_KEY, mode.value)
  } catch (e) { /* ignore */ }
  document.documentElement.setAttribute('data-theme', applied.value)
}

/** 跟随系统档实时响应系统偏好变化 */
if (typeof matchMedia !== 'undefined') {
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (mode.value === 'system') persistAndApply()
  })
}

/** @param {ThemeMode} m */
function setMode(m) {
  mode.value = m
  persistAndApply()
}

/** 三态循环:light → dark → system */
function cycleMode() {
  const order = /** @type {ThemeMode[]} */ (['light', 'dark', 'system'])
  setMode(order[(order.indexOf(mode.value) + 1) % order.length])
}

/** main.js 挂载前调用:重读 storage 并设置 data-theme,防首屏闪烁 */
export function applyThemeFromStorage() {
  mode.value = readStored()
  document.documentElement.setAttribute('data-theme', applied.value)
}

export function useTheme() {
  return { mode, applied, setMode, cycleMode }
}
