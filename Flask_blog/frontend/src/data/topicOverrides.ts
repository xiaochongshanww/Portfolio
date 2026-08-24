/**
 * 专题过渡配置(P1 关键决策:阶段内不建 Topic 表)
 *
 * 生命周期:这是临时数据源,P2 后端 Topic 实体落地后迁移为 API,
 * 本文件随之退役——不允许演进为永久双数据源。
 *
 * 基础数据(名称/计数/最新文章)来自 taxonomy + articles API;
 * 此处只补充 Category 缺失的字段:描述 / soft 底色 / 推荐起点。
 * key 为 categoryId;未配置的分类走降级路径(默认描述、按序取色、
 * 推荐起点降级为最新一篇)。
 */

export type TopicTone = 'green' | 'blue' | 'signal' | 'sand'

export interface TopicOverride {
  /** 专题卡/详情 Hero 的 soft 底色 */
  tone: TopicTone
  /** 专题一句话描述(taxonomy 的 description 恒为 null) */
  description: string
  /** 推荐起点文章 slug;缺省降级为最新一篇 */
  startArticleSlug?: string
}

/** @type {Record<number, TopicOverride>} */
export const TOPIC_OVERRIDES: Record<number, TopicOverride> = {
  // 示例(dev.db 分类 id 落定后填入):
  // 1: { tone: 'green', description: 'RAG、Agent、模型应用、评测与工程落地。', startArticleSlug: 'deep-dive-rag' },
}

export function topicOverrideFor(categoryId: number | null | undefined): TopicOverride | null {
  if (categoryId == null) return null
  return TOPIC_OVERRIDES[categoryId] ?? null
}
