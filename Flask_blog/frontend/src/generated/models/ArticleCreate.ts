/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ArticleCreate = {
    /**
     * 标题 (1-120 字)
     */
    title: string;
    /**
     * URL slug，允许小写字母/数字/连字符
     */
    slug?: string;
    /**
     * Markdown 正文
     */
    content_md?: string;
    /**
     * 摘要，<=300 字符
     */
    summary?: string;
    seo_title?: string;
    seo_desc?: string;
    featured_image?: string;
    category_id?: number;
    scheduled_at?: string;
    tags?: Array<string>;
};

