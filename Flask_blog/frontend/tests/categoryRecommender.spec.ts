import { describe, it, expect } from 'vitest';
import {
  recommendCategories,
  getRelatedCategories,
  validateCategorySelection,
} from '../src/utils/categoryRecommender';

const CATS = [
  { id: 1, name: 'Vue.js', parent_id: null },
  { id: 2, name: '前端开发', parent_id: null },
  { id: 3, name: 'Python', parent_id: 1 },
  { id: 4, name: '机器学习', parent_id: null },
];

describe('recommendCategories', () => {
  it('returns empty when no categories', () => {
    expect(recommendCategories({ title: 'x' }, [])).toEqual([]);
  });

  it('returns popular categories when no input', () => {
    const recs = recommendCategories({}, CATS);
    expect(recs.length).toBeGreaterThan(0);
    expect(recs[0].reason).toBe('热门分类推荐');
  });

  it('recommends from tags', () => {
    const recs = recommendCategories({ tags: ['vue', 'vite'] }, CATS);
    expect(recs.length).toBeGreaterThan(0);
    expect(recs.some((r) => r.category.name === 'Vue.js')).toBe(true);
  });

  it('recommends from title/content', () => {
    const recs = recommendCategories(
      { title: 'Vue 3 组合式 API 实践', content: 'composition api reactive ref' },
      CATS
    );
    expect(recs.length).toBeGreaterThan(0);
  });

  it('respects maxRecommendations and minScore', () => {
    const recs = recommendCategories(
      { title: 'Vue 3', tags: ['vue'] },
      CATS,
      { maxRecommendations: 1, minScore: 100 }
    );
    expect(recs.length).toBeLessThanOrEqual(1);
  });

  it('excludes reason when includeReason false', () => {
    const recs = recommendCategories({ tags: ['vue'] }, CATS, { includeReason: false });
    if (recs.length) {
      expect(recs[0].reason).toBeUndefined();
    }
  });
});

describe('getRelatedCategories', () => {
  it('returns empty for missing id/categories', () => {
    expect(getRelatedCategories(0, CATS)).toEqual([]);
    expect(getRelatedCategories(1, [])).toEqual([]);
    expect(getRelatedCategories(99, CATS)).toEqual([]);
  });

  it('finds siblings, children and parent', () => {
    const related = getRelatedCategories(1, CATS);
    // sibling: id 2 (same parent_id null); child: id 3 (parent_id 1)
    expect(related.map((c) => c.id)).toEqual(expect.arrayContaining([2, 3]));
    expect(related.some((c) => c.id === 2 && c.relation === '同级分类')).toBe(true);
    expect(related.some((c) => c.id === 3 && c.relation === '子分类')).toBe(true);
  });

  it('finds parent category', () => {
    const related = getRelatedCategories(3, CATS);
    expect(related.some((c) => c.id === 1 && c.relation === '父分类')).toBe(true);
  });
});

describe('validateCategorySelection', () => {
  it('valid when no id', () => {
    expect(validateCategorySelection(0, { title: 'x' }, CATS).valid).toBe(true);
  });

  it('error when category missing', () => {
    const res = validateCategorySelection(99, { title: 'x' }, CATS);
    expect(res.valid).toBe(false);
    expect(res.error).toBe('选择的分类不存在');
  });

  it('warning when category not recommended', () => {
    const res = validateCategorySelection(4, { title: 'vue' }, CATS);
    expect(res.valid).toBe(true);
    expect(res.warning).toBeTruthy();
  });

  it('no warning when recommended', () => {
    const res = validateCategorySelection(1, { title: 'Vue 3 组合式 API' }, CATS);
    expect(res.valid).toBe(true);
    expect(res.warning).toBeNull();
  });
});
