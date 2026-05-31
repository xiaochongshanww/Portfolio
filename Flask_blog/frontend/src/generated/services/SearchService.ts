/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SearchResultResponse } from '../models/SearchResultResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SearchService {
    /**
     * Search articles
     * 全文搜索文章；支持 ETag；ranking rules 纳入 likes_count, views_count, published_at
     * @param q 关键词
     * @param page
     * @param pageSize
     * @param status
     * @param tag
     * @param tags
     * @param matchMode
     * @param categoryId
     * @param authorId
     * @param sort
    * @param dateFrom 起始发布日期 (YYYY-MM-DD)
    * @param dateTo 截止发布日期 (YYYY-MM-DD)
    * @param facets 需要返回的 facets 列表 (逗号分隔，如 tags,category_id,author_id)
    * @returns SearchResultResponse OK
     * @throws ApiError
     */
    public static getApiV1Search(
        q?: string,
        page?: number,
        pageSize?: number,
        status?: string,
        tag?: string,
        tags?: string,
        matchMode?: 'any' | 'all' | 'phrase',
        categoryId?: number,
        authorId?: number,
        sort?: string,
        dateFrom?: string,
        dateTo?: string,
        facets?: string,
    ): CancelablePromise<SearchResultResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/search/',
            query: {
                'q': q,
                'page': page,
                'page_size': pageSize,
                'status': status,
                'tag': tag,
                'tags': tags,
                'match_mode': matchMode,
                'category_id': categoryId,
                'author_id': authorId,
                'sort': sort,
                'date_from': dateFrom,
                'date_to': dateTo,
                'facets': facets,
            },
            errors: {
                304: `Not Modified`,
                400: `Validation Error`,
                429: `Too Many Requests`,
                500: `Internal Server Error`,
            },
        });
    }
}
