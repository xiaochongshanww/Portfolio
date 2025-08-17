/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type BookmarkToggleResponse = {
    code?: number;
    message?: string;
    data?: {
        /**
         * bookmarked 或 removed
         */
        action?: 'bookmarked' | 'removed';
    };
};

