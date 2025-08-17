/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthResponse } from '../models/HealthResponse';
import type { StandardSuccess } from '../models/StandardSuccess';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DefaultService {
    /**
     * Ping
     * @returns StandardSuccess pong
     * @throws ApiError
     */
    public static getApiV1Ping(): CancelablePromise<StandardSuccess> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ping',
        });
    }
    /**
     * Health
     * @returns HealthResponse OK
     * @throws ApiError
     */
    public static getApiV1Health(): CancelablePromise<HealthResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/health',
        });
    }
    /**
     * Sitemap XML
     * @returns any OK
     * @throws ApiError
     */
    public static getSitemapXml(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/sitemap.xml',
        });
    }
    /**
     * Robots.txt
     * @returns any OK
     * @throws ApiError
     */
    public static getRobotsTxt(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/robots.txt',
        });
    }
}
