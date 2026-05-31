/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CommentPendingListResponse } from '../models/CommentPendingListResponse';
import type { CommentTreeResponse } from '../models/CommentTreeResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CommentsService {
    /**
     * Get comment tree for article
     * @param articleId
     * @returns CommentTreeResponse OK
     * @throws ApiError
     */
    public static getApiV1CommentsArticleTree(
        articleId: number,
    ): CancelablePromise<CommentTreeResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/comments/article/{article_id}/tree',
            path: {
                'article_id': articleId,
            },
            errors: {
                404: `Not Found`,
            },
        });
    }
    /**
     * List pending comments (moderation queue)
     * @param page
     * @param pageSize
     * @returns CommentPendingListResponse OK
     * @throws ApiError
     */
    public static getApiV1CommentsPending(
        page?: number,
        pageSize?: number,
    ): CancelablePromise<CommentPendingListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/comments/pending',
            query: {
                'page': page,
                'page_size': pageSize,
            },
            errors: {
                401: `Unauthorized`,
                403: `Forbidden`,
            },
        });
    }
}
