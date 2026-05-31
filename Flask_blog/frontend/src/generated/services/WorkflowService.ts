/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArticleVersionListResponse } from '../models/ArticleVersionListResponse';
import type { BookmarkToggleResponse } from '../models/BookmarkToggleResponse';
import type { CreateVersionResponse } from '../models/CreateVersionResponse';
import type { LikeToggleResponse } from '../models/LikeToggleResponse';
import type { RejectRequest } from '../models/RejectRequest';
import type { WorkflowStatusResponse } from '../models/WorkflowStatusResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WorkflowService {
    /**
     * Submit article
     * @param id
     * @returns WorkflowStatusResponse OK
     * @throws ApiError
     */
    public static postApiV1ArticlesSubmit(
        id: number,
    ): CancelablePromise<WorkflowStatusResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/submit',
            path: {
                'id': id,
            },
            errors: {
                400: `Validation Error`,
                403: `Forbidden`,
            },
        });
    }
    /**
     * Approve article
     * @param id
     * @returns WorkflowStatusResponse OK
     * @throws ApiError
     */
    public static postApiV1ArticlesApprove(
        id: number,
    ): CancelablePromise<WorkflowStatusResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/approve',
            path: {
                'id': id,
            },
            errors: {
                403: `Forbidden`,
            },
        });
    }
    /**
     * Reject article
     * @param id
     * @param requestBody
     * @returns WorkflowStatusResponse OK
     * @throws ApiError
     */
    public static postApiV1ArticlesReject(
        id: number,
        requestBody: RejectRequest,
    ): CancelablePromise<WorkflowStatusResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/reject',
            path: {
                'id': id,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation Error`,
                403: `Forbidden`,
            },
        });
    }
    /**
     * Schedule article
     * @param id
     * @param requestBody
     * @returns any OK
     * @throws ApiError
     */
    public static postApiV1ArticlesSchedule(
        id: number,
        requestBody: {
            scheduled_at: string;
        },
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/schedule',
            path: {
                'id': id,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation Error`,
                403: `Forbidden`,
            },
        });
    }
    /**
     * Unschedule
     * @param id
     * @returns any OK
     * @throws ApiError
     */
    public static postApiV1ArticlesUnschedule(
        id: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/unschedule',
            path: {
                'id': id,
            },
            errors: {
                400: `Validation Error`,
                403: `Forbidden`,
            },
        });
    }
    /**
     * Unpublish
     * @param id
     * @returns any OK
     * @throws ApiError
     */
    public static postApiV1ArticlesUnpublish(
        id: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/unpublish',
            path: {
                'id': id,
            },
            errors: {
                400: `Validation Error`,
                403: `Forbidden`,
            },
        });
    }
    /**
     * Toggle like
     * @param id
     * @returns LikeToggleResponse OK
     * @throws ApiError
     */
    public static postApiV1ArticlesLike(
        id: number,
    ): CancelablePromise<LikeToggleResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/like',
            path: {
                'id': id,
            },
            errors: {
                401: `Unauthorized`,
                404: `Not Found`,
                429: `Too Many Requests`,
            },
        });
    }
    /**
     * Toggle bookmark
     * @param id
     * @returns BookmarkToggleResponse OK
     * @throws ApiError
     */
    public static postApiV1ArticlesBookmark(
        id: number,
    ): CancelablePromise<BookmarkToggleResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/bookmark',
            path: {
                'id': id,
            },
            errors: {
                401: `Unauthorized`,
                404: `Not Found`,
                429: `Too Many Requests`,
            },
        });
    }
    /**
     * List article versions
     * @param id
     * @returns ArticleVersionListResponse OK
     * @throws ApiError
     */
    public static getApiV1ArticlesVersions(
        id: number,
    ): CancelablePromise<ArticleVersionListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/{id}/versions',
            path: {
                'id': id,
            },
            errors: {
                401: `Unauthorized`,
                403: `Forbidden`,
                404: `Not Found`,
            },
        });
    }
    /**
     * Create article version (snapshot current)
     * @param id
     * @returns CreateVersionResponse Created
     * @throws ApiError
     */
    public static postApiV1ArticlesVersions(
        id: number,
    ): CancelablePromise<CreateVersionResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/versions',
            path: {
                'id': id,
            },
            errors: {
                401: `Unauthorized`,
                403: `Forbidden`,
                404: `Not Found`,
            },
        });
    }
}
