/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ErrorCodeCatalogResponse } from '../models/ErrorCodeCatalogResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MetaService {
    /**
     * App version
     * @returns any OK
     * @throws ApiError
     */
    public static getApiV1MetaVersion(): CancelablePromise<{
        code?: number;
        message?: string;
        data?: {
            version?: string;
            git_commit?: string;
            build_time?: string;
        };
    }> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/meta/version',
        });
    }
    /**
     * List error codes
     * 错误码目录：用于前端统一映射展示。
     * @returns ErrorCodeCatalogResponse OK
     * @throws ApiError
     */
    public static getApiV1MetaErrorCodes(): CancelablePromise<ErrorCodeCatalogResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/meta/error-codes',
        });
    }
}
