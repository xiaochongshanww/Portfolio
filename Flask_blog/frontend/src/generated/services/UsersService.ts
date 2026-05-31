/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArticleListResponse } from '../models/ArticleListResponse';
import type { ChangeRoleResponse } from '../models/ChangeRoleResponse';
import type { ProfileUpdate } from '../models/ProfileUpdate';
import type { RoleUpdate } from '../models/RoleUpdate';
import type { UserDetailResponse } from '../models/UserDetailResponse';
import type { UserListResponse } from '../models/UserListResponse';
import type { UserPublicResponse } from '../models/UserPublicResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UsersService {
    /**
     * Get my profile
     * @returns UserDetailResponse OK
     * @throws ApiError
     */
    public static getApiV1UsersMe(): CancelablePromise<UserDetailResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/me',
            errors: {
                401: `Unauthorized`,
            },
        });
    }
    /**
     * Update my profile
     * @param requestBody
     * @returns UserDetailResponse Updated
     * @throws ApiError
     */
    public static patchApiV1UsersMe(
        requestBody: ProfileUpdate,
    ): CancelablePromise<UserDetailResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/users/me',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation Error`,
                401: `Unauthorized`,
            },
        });
    }
    /**
     * List users (admin)
     * 支持 ETag / If-None-Match
     * @param page
     * @param pageSize
     * @returns UserListResponse OK
     * @throws ApiError
     */
    public static getApiV1Users(
        page?: number,
        pageSize?: number,
    ): CancelablePromise<UserListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/',
            query: {
                'page': page,
                'page_size': pageSize,
            },
            errors: {
                304: `Not Modified`,
                403: `Forbidden`,
            },
        });
    }
    /**
     * Change user role
     * @param userId
     * @param requestBody
     * @returns ChangeRoleResponse OK
     * @throws ApiError
     */
    public static patchApiV1UsersRole(
        userId: number,
        requestBody: RoleUpdate,
    ): CancelablePromise<ChangeRoleResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/users/{user_id}/role',
            path: {
                'user_id': userId,
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
     * Public author profile
     * 支持 ETag / If-None-Match
     * @param userId
     * @returns UserPublicResponse OK
     * @throws ApiError
     */
    public static getApiV1UsersPublic(
        userId: number,
    ): CancelablePromise<UserPublicResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/public/{user_id}',
            path: {
                'user_id': userId,
            },
            errors: {
                304: `Not Modified`,
                404: `Not Found`,
            },
        });
    }
    /**
     * Public author published articles
     * 支持 ETag / If-None-Match
     * @param userId
     * @param page
     * @param pageSize
     * @param sort
     * @returns ArticleListResponse OK
     * @throws ApiError
     */
    public static getApiV1UsersPublicArticles(
        userId: number,
        page?: number,
        pageSize?: number,
        sort?: string,
    ): CancelablePromise<ArticleListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/public/{user_id}/articles',
            path: {
                'user_id': userId,
            },
            query: {
                'page': page,
                'page_size': pageSize,
                'sort': sort,
            },
            errors: {
                304: `Not Modified`,
                404: `Not Found`,
            },
        });
    }
}
