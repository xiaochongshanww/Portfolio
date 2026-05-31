/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuditLogEntry } from './AuditLogEntry';
import type { PaginationMeta } from './PaginationMeta';
export type AuditLogListResponse = {
    code?: number;
    message?: string;
    data?: (PaginationMeta & {
        list?: Array<AuditLogEntry>;
    });
};

