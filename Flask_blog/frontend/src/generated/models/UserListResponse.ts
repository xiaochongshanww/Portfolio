/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PaginationMeta } from './PaginationMeta';
import type { UserDetail } from './UserDetail';
export type UserListResponse = {
    code?: number;
    message?: string;
    data?: (PaginationMeta & {
        list?: Array<UserDetail>;
    });
};

