/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArticleSummary } from './ArticleSummary';
export type SearchResultItem = (ArticleSummary & {
    /**
     * 高亮片段
     */
    highlight?: Record<string, any> | null;
    /**
     * 搜索相关性得分
     */
    score?: number | null;
});

