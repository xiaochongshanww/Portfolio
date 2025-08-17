/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChangePasswordRequest } from '../models/ChangePasswordRequest';
import type { LoginRequest } from '../models/LoginRequest';
import type { LoginResponse } from '../models/LoginResponse';
import type { RefreshResponse } from '../models/RefreshResponse';
import type { RegisterRequest } from '../models/RegisterRequest';
import type { RegisterResponse } from '../models/RegisterResponse';
import type { StandardSuccess } from '../models/StandardSuccess';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
    /**
     * Register
     * @param requestBody
     * @returns RegisterResponse Created
     * @throws ApiError
     */
    public static postApiV1AuthRegister(
        requestBody: RegisterRequest,
    ): CancelablePromise<RegisterResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/register',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation Error`,
                409: `Conflict`,
            },
        });
    }
    /**
     * Login
     * @param requestBody
     * @returns LoginResponse OK
     * @throws ApiError
     */
    public static postApiV1AuthLogin(
        requestBody: LoginRequest,
    ): CancelablePromise<LoginResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/login',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation Error`,
                401: `Unauthorized`,
            },
        });
    }
    /**
     * Refresh access token
     * @returns RefreshResponse OK
     * @throws ApiError
     */
    public static postApiV1AuthRefresh(): CancelablePromise<RefreshResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/refresh',
            errors: {
                401: `Unauthorized`,
            },
        });
    }
    /**
     * Logout
     * @returns StandardSuccess OK
     * @throws ApiError
     */
    public static postApiV1AuthLogout(): CancelablePromise<StandardSuccess> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/logout',
        });
    }
    /**
     * Change password
     * @param requestBody
     * @returns StandardSuccess OK
     * @throws ApiError
     */
    public static postApiV1AuthChangePassword(
        requestBody: ChangePasswordRequest,
    ): CancelablePromise<StandardSuccess> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/change_password',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Validation Error`,
                401: `Unauthorized`,
            },
        });
    }
}
