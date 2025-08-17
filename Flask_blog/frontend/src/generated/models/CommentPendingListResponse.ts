/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Comment } from './Comment';
import type { PaginationMeta } from './PaginationMeta';
export type CommentPendingListResponse = {
    code?: number;
    message?: string;
    data?: (PaginationMeta & {
        list?: Array<Comment>;
    });
};

