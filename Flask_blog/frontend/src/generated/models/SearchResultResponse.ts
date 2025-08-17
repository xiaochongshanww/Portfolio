/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PaginationMeta } from './PaginationMeta';
import type { SearchResultItem } from './SearchResultItem';
export type SearchResultResponse = {
    code?: number;
    message?: string;
    data?: (PaginationMeta & {
        query?: string | null;
        filters?: {
            status?: 'draft' | 'pending_review' | 'rejected' | 'scheduled' | 'published' | 'archived' | null;
            tags?: Array<string>;
            category_id?: number | null;
            author_id?: number | null;
            match_mode?: 'default' | 'all' | 'any' | 'exact' | null;
            sort?: 'published_at_desc' | 'published_at_asc' | 'score_desc' | 'views_desc' | null;
        };
        list?: Array<SearchResultItem>;
    });
};

