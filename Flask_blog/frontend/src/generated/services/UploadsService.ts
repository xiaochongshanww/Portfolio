/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UploadImageResponse } from '../models/UploadImageResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UploadsService {
    /**
     * Upload image
     * @param formData
     * @returns UploadImageResponse OK
     * @throws ApiError
     */
    public static postApiV1UploadsImage(
        formData: {
            file: Blob;
        },
    ): CancelablePromise<UploadImageResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/uploads/image',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                400: `Validation Error`,
                401: `Unauthorized`,
                413: `Payload Too Large`,
                415: `Unsupported Media Type`,
                429: `Too Many Requests`,
            },
        });
    }
}
