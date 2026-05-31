/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArticleCreate } from '../models/ArticleCreate';
import type { ArticleDetailResponse } from '../models/ArticleDetailResponse';
import type { ArticleListResponse } from '../models/ArticleListResponse';
import type { ArticleUpdate } from '../models/ArticleUpdate';
import type { ArticleVersionListResponse } from '../models/ArticleVersionListResponse';
import type { BookmarkToggleResponse } from '../models/BookmarkToggleResponse';
import type { CreateVersionResponse } from '../models/CreateVersionResponse';
import type { DeleteArticleResponse } from '../models/DeleteArticleResponse';
import type { LikeToggleResponse } from '../models/LikeToggleResponse';
import type { RejectRequest } from '../models/RejectRequest';
import type { WorkflowStatusResponse } from '../models/WorkflowStatusResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ArticlesService {
    /**
     * Create article
     * @param requestBody
     * @returns ArticleDetailResponse Created
     * @throws ApiError
     */
    public static postApiV1Articles(
        requestBody: ArticleCreate,
    ): CancelablePromise<ArticleDetailResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation Error`,
                401: `Unauthorized`,
                403: `Forbidden`,
                409: `Conflict`,
                429: `Too Many Requests`,
                500: `Internal Server Error`,
            },
        });
    }
    /**
     * List articles
     * 支持 ETag / If-None-Match
     * @param page
     * @param pageSize
     * @param status
     * @param tag
     * @param category
     * @returns ArticleListResponse OK
     * @throws ApiError
     */
    public static getApiV1Articles(
        page?: number,
        pageSize?: number,
        status?: string,
        tag?: string,
        category?: string,
    ): CancelablePromise<ArticleListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/',
            query: {
                'page': page,
                'page_size': pageSize,
                'status': status,
                'tag': tag,
                'category': category,
            },
            errors: {
                304: `Not Modified`,
                401: `Unauthorized`,
                429: `Too Many Requests`,
                500: `Internal Server Error`,
            },
        });
    }
    /**
     * Get article detail
     * 支持 ETag / If-None-Match
     * @param id
     * @returns ArticleDetailResponse OK
     * @throws ApiError
     */
    public static getApiV1Articles1(
        id: number,
    ): CancelablePromise<ArticleDetailResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/{id}',
            path: {
                'id': id,
            },
            errors: {
                304: `Not Modified`,
                401: `Unauthorized`,
                404: `Not Found`,
                500: `Internal Server Error`,
            },
        });
    }
    /**
     * Update article
     * @param id
     * @param requestBody
     * @returns ArticleDetailResponse OK
     * @throws ApiError
     */
    public static putApiV1Articles(
        id: number,
        requestBody: ArticleUpdate,
    ): CancelablePromise<ArticleDetailResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/articles/{id}',
            path: {
                'id': id,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation Error`,
                401: `Unauthorized`,
                403: `Forbidden`,
                404: `Not Found`,
                409: `Conflict`,
                429: `Too Many Requests`,
                500: `Internal Server Error`,
            },
        });
    }
    /**
     * Delete article
     * @param id
     * @returns DeleteArticleResponse OK
     * @throws ApiError
     */
    public static deleteApiV1Articles(
        id: number,
    ): CancelablePromise<DeleteArticleResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/articles/{id}',
            path: {
                'id': id,
            },
            errors: {
                401: `Unauthorized`,
                403: `Forbidden`,
                404: `Not Found`,
                429: `Too Many Requests`,
                500: `Internal Server Error`,
            },
        });
    }
    /**
     * Get article by slug (internal)
     * 支持 ETag / If-None-Match
     * @param slug
     * @returns ArticleDetailResponse OK
     * @throws ApiError
     */
    public static getApiV1ArticlesSlug(
        slug: string,
    ): CancelablePromise<ArticleDetailResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/slug/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                304: `Not Modified`,
                404: `Not Found`,
            },
        });
    }
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
     * Public list published articles
     * 支持 ETag / If-None-Match
     * @param page
     * @param pageSize
     * @param tag
     * @param categoryId
     * @param authorId
     * @param sort
     * @returns ArticleListResponse OK
     * @throws ApiError
     */
    public static getApiV1ArticlesPublic(
        page?: number,
        pageSize?: number,
        tag?: string,
        categoryId?: number,
        authorId?: number,
        sort?: string,
    ): CancelablePromise<ArticleListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/public/',
            query: {
                'page': page,
                'page_size': pageSize,
                'tag': tag,
                'category_id': categoryId,
                'author_id': authorId,
                'sort': sort,
            },
            errors: {
                304: `Not Modified`,
                429: `Too Many Requests`,
                500: `Internal Server Error`,
            },
        });
    }
    /**
     * Public get article by slug
     * 支持 ETag / If-None-Match；views_count 为近实时去重浏览次数(同用户或 IP+UA 1 小时内只计 1 次)
     * @param slug
     * @returns ArticleDetailResponse OK
     * @throws ApiError
     */
    public static getApiV1ArticlesPublicSlug(
        slug: string,
    ): CancelablePromise<ArticleDetailResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/public/slug/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                304: `Not Modified`,
                404: `Not Found`,
                429: `Too Many Requests`,
                500: `Internal Server Error`,
            },
        });
    }
    /**
     * Public hot articles ranking
     * 基于窗口(默认48h)的去重浏览+点赞+时间衰减组合得分。score = log10(views+1)*0.7 + likes*0.5 + 1/(1+hours/24)。支持 page,page_size,window_hours。支持 ETag / If-None-Match
     * @param page
     * @param pageSize
     * @param windowHours 统计窗口(小时)，默认48，最大168(7天)
     * @returns ArticleListResponse OK
     * @throws ApiError
     */
    public static getApiV1ArticlesPublicHot(
        page?: number,
        pageSize?: number,
        windowHours?: number,
    ): CancelablePromise<ArticleListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/public/hot',
            query: {
                'page': page,
                'page_size': pageSize,
                'window_hours': windowHours,
            },
            errors: {
                304: `Not Modified`,
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
        detail?: boolean,
    ): CancelablePromise<ArticleVersionListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/{id}/versions',
            path: {
                'id': id,
            },
            query: {
                'detail': detail ? '1' : undefined,
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
    /**
     * Get single version detail
     * @param id
     * @param versionNo
     * @returns any OK
     * @throws ApiError
     */
    public static getApiV1ArticlesVersionsVersion(
        id: number,
        versionNo: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/articles/{id}/versions/{version_no}',
            path: {
                'id': id,
                'version_no': versionNo,
            },
            errors: {
                401: `Unauthorized`,
                403: `Forbidden`,
                404: `Not Found`,
            },
        });
    }
    /**
     * Rollback to version
     * @param id
     * @param versionNo
     * @returns any OK
     * @throws ApiError
     */
    public static postApiV1ArticlesVersionsRollback(
        id: number,
        versionNo: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/articles/{id}/versions/{version_no}/rollback',
            path: {
                'id': id,
                'version_no': versionNo,
            },
            errors: {
                401: `Unauthorized`,
                403: `Forbidden`,
                404: `Not Found`,
            },
        });
    }
}
