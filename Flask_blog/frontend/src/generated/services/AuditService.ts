/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuditLogListResponse } from '../models/AuditLogListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuditService {
    /**
     * List audit logs
     * @param page
     * @param pageSize
     * @param articleId
     * @param action
     * @returns AuditLogListResponse OK
     * @throws ApiError
     */
    public static getApiV1AuditLogs(
        page?: number,
        pageSize?: number,
        articleId?: number | null,
        action?: string | null,
    ): CancelablePromise<AuditLogListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/audit/logs',
            query: {
                'page': page,
                'page_size': pageSize,
                'article_id': articleId,
                'action': action,
            },
            errors: {
                401: `Unauthorized`,
                403: `Forbidden`,
            },
        });
    }
}
