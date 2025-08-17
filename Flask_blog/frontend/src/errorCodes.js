// DEPRECATED: 请使用 src/governance/errorCodes.generated.ts 中的 ERROR_CODE_MAP
export const ERROR_CODE_MAP = new Map([
  [0, '成功'],
  [1001, '参数校验失败'],
  [1002, '唯一约束冲突'],
  [2001, '认证失效，请重新登录'],
  [2002, '无权限执行该操作'],
  [2003, '操作过于频繁，请稍后再试'],
  [3001, '当前状态不允许该操作'],
  [3002, '状态冲突，请刷新后再试'],
  [4001, '资源不存在或已删除'],
  [5000, '服务器开小差了']
]);
export function translateError(code, fallback){
  console.warn('[deprecated] translateError 请改为直接使用治理生成的 ERROR_CODE_MAP');
  return ERROR_CODE_MAP.get(code) || fallback || '操作失败';
}
