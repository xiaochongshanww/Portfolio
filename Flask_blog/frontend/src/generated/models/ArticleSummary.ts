/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ArticleSummary = {
    id?: number;
    title?: string;
    slug?: string;
    status?: 'draft' | 'pending_review' | 'rejected' | 'scheduled' | 'published' | 'archived';
    published_at?: string | null;
    created_at?: string | null;
    tags?: Array<string>;
    likes_count?: number;
    /**
     * 近实时去重浏览次数
     */
    views_count?: number;
    /**
     * 热门/搜索时的得分
     */
    score?: number | null;
};

