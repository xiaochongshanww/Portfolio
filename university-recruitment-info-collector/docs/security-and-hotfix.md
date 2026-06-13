# Security & Hotfix Log (2026-06)

## 已修复问题

### 1. API Key 硬编码泄露 (CRITICAL)
- **问题**: `config.py` 中硬编码了 DeepSeek API Key `sk-378e29cb7dd54caf9c711a225e0cbb43`
- **修复**: 删除所有硬编码 Key，`LLM_API_KEY` 仅从环境变量读取
- **影响**: 旧 Key 已在代码和 Git 历史中暴露，**必须立即在 DeepSeek 后台吊销**
- **处置**: 登录 https://platform.deepseek.com → API Keys → 删除/重新生成

### 2. 浏览器文本采集器 LLM 调用参数错误
- **问题**: `BrowserTalentSiteAdapter._extract_text_jobs_from_soup()` 调用 `llm.extract(description, position)` 但 `extract()` 只接受一个参数
- **修复**: 改为 `llm.extract(description)`，增加最小正文长度检查，异常记录到日志
- **影响**: 之前文本模式 LLM 增强静默失败，所有异常被 `except Exception: pass` 吞掉

### 3. Naive/Aware Datetime 混合导致崩溃
- **问题**: 旧数据库 `collected_at` 可能无时区，与新 UTC datetime 混合时 `max()` 和比较操作抛 TypeError
- **修复**: 新增 `ensure_utc()` 函数，所有读取路径统一 UTC 规范化

### 4. URL 日期推断接受非法日期
- **问题**: `extract_date_from_url()` 只做范围检查（d≤31），`2026-02-31` 等非法日期在后续 `date.fromisoformat()` 抛 ValueError
- **修复**: 内部使用 `date(year, month, day)` 构造验证，返回 `date | None`

### 5. LLM 字段输出无校验
- **问题**: LLM 返回的字段仅检查是否是字符串，接受任意值
- **修复**: 新增 `LlmExtractedFields` Pydantic 模型，校验学历枚举、岗位类型枚举、department 后缀、黑名单值。Markdown JSON 代码块可正常解析

### 6. LLM clean_position 覆盖原始标题
- **问题**: LLM 清洗的 `clean_position` 直接覆盖 `position`，不同公告被洗成相同标题后导致错误去重
- **修复**: 新增 `normalized_position` 字段存储 LLM 清洗结果，`position` 保持原始值不被覆盖

### 7. CORS 配置安全
- **修复**: 生产环境不允许默认 `*`，不允许 `allow_origins=["*"]` + `allow_credentials=True` 同时存在

### 8. 外部链接安全
- **修复**: `window.open(url, '_blank', 'noopener,noreferrer')` + URL 协议白名单检查

### 9. LLM 用量限制
- **修复**: `LLM_MAX_JOBS` 默认值从 20 降至 5，防止客户端无限扩大 LLM 分析数

## 数据库兼容修改
- `recruitment_jobs` 新增 `normalized_position TEXT` 列（自动迁移）
- datetime 读取统一 UTC 规范化，旧数据自动兼容

## API 行为变化
- `LLM_MAX_JOBS` 默认 5
- `/match` 限流默认 10req/60s
- API_ACCESS_TOKEN 为空时无需认证

## 仍存在的限制
- 限流为内存实现，仅单进程有效
- 旧 API Key 需人工在 DeepSeek 后台吊销
- Git 历史中的 Key 无法自动清除（不重写历史）
