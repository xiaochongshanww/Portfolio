# Engineering Refactor (2026-06)

## 改造内容

### 一、稳定岗位 ID
- 新增 `url_utils.py`：URL 规范化 + SHA-256 ID 生成
- 所有采集器统一使用 `generate_job_id(normalize_url(url))` 
- ID 格式：`job-{sha256[:24]}`，与页面排序无关
- 同一 URL 多次采集生成相同 ID

### 二、岗位生命周期
- 新增字段：`first_seen_at`, `last_seen_at`, `last_changed_at`, `content_hash`, `removed_at`, `status`
- Status: `active | expired | removed | unknown`
- 首次发现写入 `first_seen_at`，再次发现更新 `last_seen_at`
- 内容变化时更新 `last_changed_at` 和 `content_hash`
- 过期自动标记 `expired`，成功后标记未出现岗位为 `removed`
- 采集失败时不标记 removed

### 三、采集运行记录
- 新增表：`collection_runs`, `collection_source_runs`
- 每次采集创建运行记录，每个信息源单独记录
- 支持健康报告基于最近运行结果

### 四、匹配规则重写
- 学历使用结构化等级（本科<硕士<博士），支持"及以上"语义
- 限制条件支持肯定/否定/未知三态
- 新增 `school_metadata.py` 支持学校类型匹配
- MatchResult 增加 `confidence_score`, `hard_constraint_passed`, `hard_constraint_failures`
- 得分从 0 开始根据证据累加，硬性不满足不进入默认结果

### 五、LLM 批量优化
- 从逐条串行改为批量请求（最多 20 个候选岗位）
- 最终分 = 规则分 × 0.7 + 语义分 × 0.3
- 批量响应使用 Pydantic 校验
- 新增超时和日额度限制

### 六、API 安全
- CORS 通过环境变量配置，生产环境默认不开放
- 可选 Bearer Token 验证
- `/match` 限流
- AI 增强单独额度限制
- 请求 ID 追踪，不记录用户画像

### 七、前端改进
- 用户画像使用 sessionStorage，不再出现在 URL
- 按钮改为"AI 增强匹配"
- 显示置信度、硬性条件状态
- 链接使用 `noopener,noreferrer`
- 提交时禁用重复点击

### 八、采集并发
- HTTP 源并发 5（可配置），Playwright 源串行
- 支持重试和指数退避
- SQLite WAL 模式写入安全

## 数据库结构变化

### recruitment_jobs 新增列
| 列名 | 类型 | 说明 |
|---|---|---|
| status | TEXT | active/expired/removed/unknown |
| first_seen_at | TEXT | 首次发现时间 |
| last_seen_at | TEXT | 最后出现时间 |
| last_changed_at | TEXT | 内容最后变化时间 |
| content_hash | TEXT | 内容 SHA-256 |
| removed_at | TEXT | 标记移除时间 |

### 新增表
- `collection_runs` — 采集运行记录
- `collection_source_runs` — 信息源级运行记录
- `schema_version` — 版本迁移跟踪

### 迁移
- 自动检测并执行迁移，无需手动操作
- 现有数据库兼容，旧数据 status 默认为 'active'

## 兼容性说明
- 现有 CLI 命令保持兼容
- API 响应格式新增字段，旧字段不变
- 岗位 ID 变为 hash 格式（不与旧 ID 兼容，需重新采集）

## 已知限制
- 限流为内存实现，单进程有效
- 并发仅限 HTTP 源，Playwright 仍然串行
- 原始页面归档功能已设计但未完全实现
- 未引入完整日志系统

## 后续建议
1. 实现原始页面归档
2. 引入结构化日志（structlog）
3. 增加端到端测试
4. 引入 Redis 限流（多进程场景）
5. Playwright 浏览器池复用
