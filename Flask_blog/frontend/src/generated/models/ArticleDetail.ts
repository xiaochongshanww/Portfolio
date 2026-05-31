/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArticleSummary } from './ArticleSummary';
export type ArticleDetail = (ArticleSummary & {
    /**
     * 清洗后的安全 HTML
     */
    content_html?: string;
    content_md?: string;
    summary?: string;
    seo_title?: string;
    seo_desc?: string;
});

