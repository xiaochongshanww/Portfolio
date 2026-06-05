// 自动生成: 请勿手工编辑
export const ERROR_CODE_MAP = new Map([
  [0, '成功'],
  [1001, '参数校验失败'],
  [1002, '唯一约束冲突'],
  [2001, '未认证或令牌失效'],
  [2002, '无权限'],
  [2003, '触发频率限制'],
  [3001, '当前状态不允许该操作'],
  [3002, '状态机并发冲突'],
  [4001, '资源不存在'],
  [5000, '服务器内部错误'],
]);

export function translateError(code, fallback){
  return ERROR_CODE_MAP.get(code) || fallback || '操作失败';
}