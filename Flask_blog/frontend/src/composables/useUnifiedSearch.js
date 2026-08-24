/**
 * 统一搜索(B2):聚合 文章 / 专题 / 项目 三类来源,返回统一结构。
 * - 文章:后端 /search(MeiliSearch 可用时走它;不可用时后端自身降级 LIKE,前端只管不抛错)
 * - 专题:taxonomy categories + topicOverrides 的名称/描述匹配
 * - 项目:Project API(P2 实体化,impl-P2 分组 A)
 * 空关键词不发起任何请求。
 */
import { API } from '../api'
import { topicOverrideFor } from '../data/topicOverrides'

/**
 * @typedef {Object} UnifiedResult
 * @property {'article'|'topic'|'project'} type
 * @property {string} title
 * @property {string} snippet
 * @property {string} meta 结果行右侧的类型/归属文案
 * @property {string} href
 */

const SEARCH_PAGE_SIZE = 20

/** 文章来源:搜索接口失败时静默降级为公开列表本地过滤
 * @param {string} q
 * @returns {Promise<UnifiedResult[]>}
 */
async function searchArticles(q) {
  try {
    const resp = await API.SearchService.search({ q, page: 1, page_size: SEARCH_PAGE_SIZE })
    const data = resp?.data?.data ?? resp?.data ?? {}
    const list = data?.list ?? []
    return list.map(
      (/** @type {any} */ r) =>
        /** @type {UnifiedResult} */ ({
          type: 'article',
          title: r.title || '',
          snippet: r.highlight?.content || r.excerpt || r.summary || '',
          meta: r.category ? `文章 · ${r.category}` : '文章',
          href: r.slug ? `/article/${r.slug}` : '',
        }),
    )
  } catch (e) {
    // 后端搜索不可用:降级为公开文章列表 + 前端包含匹配
    try {
      const resp = await API.getPublicArticles({ page: 1, page_size: 50 })
      const list = resp?.data?.data?.list ?? []
      const k = q.toLowerCase()
      return list
        .filter(
          (/** @type {any} */ a) =>
            String(a.title || '').toLowerCase().includes(k) ||
            String(a.summary || '').toLowerCase().includes(k),
        )
        .map(
          (/** @type {any} */ a) =>
            /** @type {UnifiedResult} */ ({
              type: 'article',
              title: a.title || '',
              snippet: a.summary || a.content_excerpt || '',
              meta: a.category ? `文章 · ${a.category}` : '文章',
              href: a.slug ? `/article/${a.slug}` : '',
            }),
        )
    } catch (e2) {
      return []
    }
  }
}

/** 专题来源:taxonomy + overrides 的名称/描述匹配
 * @param {string} q
 * @returns {Promise<UnifiedResult[]>}
 */
async function searchTopics(q) {
  try {
    const resp = await API.getPublicTaxonomy()
    const cats = resp?.data?.data?.categories ?? []
    const k = q.toLowerCase()
    return cats
      .filter((/** @type {any} */ c) => {
        const desc = topicOverrideFor(c.id)?.description || c.description || ''
        return (
          String(c.name || '').toLowerCase().includes(k) ||
          String(desc || '').toLowerCase().includes(k)
        )
      })
      .map(
        (/** @type {any} */ c) =>
          /** @type {UnifiedResult} */ ({
            type: 'topic',
            title: c.name || '',
            snippet: topicOverrideFor(c.id)?.description || c.description || '长期维护的知识主题。',
            meta: `专题 · ${c.article_count ?? 0} 篇`,
            href: `/topics/${c.slug || c.id}`,
          }),
      )
  } catch (e) {
    return []
  }
}

/** 项目来源:Project API(P2)本地过滤
 * @param {string} q
 * @returns {Promise<UnifiedResult[]>}
 */
async function searchProjects(q) {
  try {
    const resp = await API.getPublicProjects()
    /** @type {any[]} */
    const items = resp?.data?.data?.list || []
    const k = q.toLowerCase()
    /** @type {Record<string,string>} */
    const statusLabel = { active: '开发中', paused: '暂停', archived: '已归档' }
    return items
      .filter(
        (p) =>
          String(p.name || '').toLowerCase().includes(k) ||
          String(p.description || '').toLowerCase().includes(k),
      )
      .map((p) => ({
        type: /** @type {const} */ ('project'),
        title: p.name || '',
        snippet: p.description || '',
        meta: `项目 · ${statusLabel[p.status] || p.status || ''}`,
        href: `/projects/${p.slug}`,
      }))
  } catch (e) {
    return []
  }
}

/**
 * @param {string} q 非空关键词
 * @returns {Promise<{results: UnifiedResult[], counts: {all:number, article:number, topic:number, project:number}}>}
 */
export async function unifiedSearch(q) {
  const keyword = String(q ?? '').trim()
  if (!keyword) return { results: [], counts: { all: 0, article: 0, topic: 0, project: 0 } }

  const [articles, topics, projects] = await Promise.all([
    searchArticles(keyword),
    searchTopics(keyword),
    searchProjects(keyword),
  ])
  const results = [...articles, ...topics, ...projects]
  const counts = {
    all: results.length,
    article: results.filter((r) => r.type === 'article').length,
    topic: results.filter((r) => r.type === 'topic').length,
    project: results.filter((r) => r.type === 'project').length,
  }
  return { results, counts }
}
