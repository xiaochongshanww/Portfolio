export const ERROR_CODE_MAP = new Map<number, string>([
  [0, "ok"], // 成功
  // 统一校验错误码
  [1001, "validation_error"], // 历史/备用
  [4001, "validation_error"], // 参数校验失败（后端实际使用）
  [1002, "duplicate_resource"], // 唯一约束冲突
  [2001, "unauthorized"], // 未认证或令牌失效
  [2002, "forbidden"], // 无权限
  [2003, "rate_limited"], // 触发频率限制
  [3001, "workflow_invalid_state"], // 当前状态不允许该操作
  [3002, "workflow_transition_conflict"], // 状态机并发冲突
  [4040, "not_found"], // 资源不存在
  [4090, "duplicate_resource"], // 冲突（如邮箱已存在、slug 冲突）
  [5000, "internal_error"], // 服务器内部错误
]);
