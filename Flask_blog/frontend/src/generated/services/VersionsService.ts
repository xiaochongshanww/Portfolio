/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArticleVersionListResponse } from '../models/ArticleVersionListResponse';
import type { CreateVersionResponse } from '../models/CreateVersionResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class VersionsService {
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
