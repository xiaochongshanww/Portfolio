/**
 * 分类/标签 → TechnicalVisual 类型映射(C5 权宜策略)
 * 关键词匹配;无命中返回空,Feed 行自动隐藏 visual 列。
 * 注意:这是过渡方案,后续可为文章增加显式 visual 字段。
 */

/** @type {Array<{keywords: string[], type: string}>} */
const RULES = [
  { keywords: ['rag', '检索', 'embedding', 'ai 工程'], type: 'rag' },
  { keywords: ['git', 'rebase', '版本控制'], type: 'git' },
  { keywords: ['jwt', 'token', '认证', '登录'], type: 'token' },
  { keywords: ['权限', 'rbac', '架构', '归属'], type: 'arch' },
]

/**
 * @param {string | undefined} [categoryName]
 * @param {string[]} [tags]
 * @returns {string} visual type 或 ''(不渲染)
 */
export function visualTypeFor(categoryName, tags) {
  const haystacks = [String(categoryName || '').toLowerCase()]
  for (const t of tags || []) haystacks.push(String(t).toLowerCase())
  for (const rule of RULES) {
    for (const kw of rule.keywords) {
      if (haystacks.some((h) => h.includes(kw))) return rule.type
    }
  }
  return ''
}
