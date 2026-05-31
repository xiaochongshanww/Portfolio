/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type UploadImageResponse = {
    code?: number;
    message?: string;
    data?: {
        url?: string;
        width?: number | null;
        height?: number | null;
        size?: number;
        variants?: Array<{
            label?: string;
            url?: string;
            width?: number;
            height?: number;
            size?: number;
        }>;
        webp?: {
            url?: string;
            width?: number;
            height?: number;
            size?: number;
        } | null;
    };
};

