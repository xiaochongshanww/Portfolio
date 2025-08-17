import { ERROR_CODE_MAP } from './errorCodes.generated';
import { ROLE_MATRIX } from './roleMatrix.generated';
import { WORKFLOW_TRANSITIONS } from './workflowTransitions.generated';

export { ERROR_CODE_MAP, ROLE_MATRIX, WORKFLOW_TRANSITIONS };

export function canRole(role: string, needed: string | string[]) {
  const list = Array.isArray(needed) ? needed : [needed];
  return list.includes(role);
}
export function canPermission(role: string, permission: string){
  const allowed = ROLE_MATRIX[permission] || [];
  return allowed.includes(role);
}
export function nextStatuses(current: string){
  return WORKFLOW_TRANSITIONS[current] || [];
}
