/**
 * Shiki 高亮封装:复用全局缓存 highlighter,失败时由调用方降级为纯文本。
 * 与 markdownProcessor.reliable.js 的主题保持一致(github-light)。
 */
import { createHighlighter } from 'shiki'

/** 复用全局缓存的 highlighter promise(单例) */
let highlighterPromise: ReturnType<typeof createHighlighter> | null = null
/** @type {Set<string>} */
const loadedLangs = new Set()

const BASE_LANGS = [
  'javascript', 'typescript', 'python',
  'html', 'css', 'json', 'yaml',
  'bash', 'shell', 'sql', 'java', 'go', 'rust',
  'vue', 'markdown', 'text',
]

const LANG_ALIASES: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  sh: 'bash',
  yml: 'yaml',
  jsx: 'javascript',
  tsx: 'typescript',
}

async function getHighlighter() {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighter({ themes: ['github-light'], langs: BASE_LANGS })
  }
  return highlighterPromise
}

/**
 * 高亮代码,返回 shiki html。
 * @param {string} code
 * @param {string} language
 */
export async function highlightCode(code: string | null | undefined, language: string | undefined) {
  const lang = (language && LANG_ALIASES[language]) || language || 'text'
  const highlighter = await getHighlighter()
  const langs = /** @type {any[]} */ (highlighter.getLoadedLanguages?.() ?? [])
  let target = lang
  if (!langs.includes(lang)) {
    try {
      type ShikiLangInput = Parameters<typeof highlighter.loadLanguage>[0]
      await highlighter.loadLanguage(lang as unknown as ShikiLangInput)
      loadedLangs.add(lang)
    } catch (e) {
      target = 'text'
    }
  }
  return highlighter.codeToHtml(String(code ?? ''), { lang: target, theme: 'github-light' })
}
