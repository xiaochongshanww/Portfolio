/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArticleSummary } from './ArticleSummary';
import type { PaginationMeta } from './PaginationMeta';
export type ArticleListResponse = {
    code?: number;
    message?: string;
    data?: (PaginationMeta & {
        list?: Array<ArticleSummary>;
    });
};

