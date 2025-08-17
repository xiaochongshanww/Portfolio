# Backend

## Setup (Local Dev)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
python run.py
```

或首次初始化：
```
flask db init  # 首次
flask db migrate -m "init"
flask db upgrade
```

迁移使用说明参见 `migrations/README_migrations.md`。

## Health
- GET /api/v1/health 返回: db/redis/search/version 状态；code=0 正常，非 0 表示降级。
- GET /api/v1/meta/version 返回: version / git_commit / build_time。

## Docker / Compose
```
# 构建并启动 (后台)
docker compose up -d --build
# 查看日志
docker compose logs -f backend
```
服务：
- backend: Flask + Gunicorn (端口 8000)
- celery_worker: 任务执行（定时发布）
- celery_beat: 调度
- db: PostgreSQL 16
- redis: 缓存/限流/队列
- meili: MeiliSearch 7700

环境变量可在 `docker-compose.yml` 中修改（JWT_SECRET_KEY / DATABASE_URL 等）。

## API Documentation
- OpenAPI JSON: GET /api/openapi.json (当前版本 0.6.6)

## Celery (scheduled publish)
```
celery -A app.tasks.celery_app worker -l info
celery -A app.tasks.celery_app beat -l info
```
定时发布：状态 scheduled 且时间到 -> published。

## Rate Limiting
- 全局默认: 200/min, 2000/day
- /api/v1/ping 10/sec
- 注册 5/min, 登录 10/min, 修改密码 5/min
- 搜索 30/min

## Caching
- 详情 300s / 列表 120s / 搜索 60s
- 写操作/状态变更后失效（包含 search:*）

## Security
- 安全响应头 / JWT + refresh 黑名单 / 限流 / markdown 清洗

## Auth
- Access + Refresh / 修改密码触发所有 refresh 撤销

## Metrics (/metrics)
Prometheus 暴露：
- app_http_requests_total{method,path,status}
- app_http_request_duration_seconds_bucket/sum/count
- app_article_published_total{source="approve|schedule"}
- app_search_queries_total
- app_search_zero_result_total

示例 PromQL：
```
# QPS (5m)
sum(rate(app_http_requests_total[5m]))
# P95 时延 (基于 histogram)
histogram_quantile(0.95, sum(rate(app_http_request_duration_seconds_bucket[5m])) by (le))
# 每分钟发布文章数
sum(increase(app_article_published_total[1m]))
# 搜索零结果率
sum(increase(app_search_zero_result_total[5m])) / sum(increase(app_search_queries_total[5m]))
```

## API (概要)
Auth:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- POST /api/v1/auth/change_password

Articles: 见 openapi.json

Comments / Search 同上。

## Version Diff
- unified diff 数组，可前端高亮。

## Tests
```
pytest -q
```

## OpenAPI 规范导出

在代码动态生成规范的基础上，可生成静态文件用于前端集成或 CI 发布:

```
python -m scripts.export_openapi  # 输出 backend/openapi.json
python -m scripts.export_openapi ../docs/openapi.v1.json  # 指定路径
```

可在 CI 流程中执行并将产物上传到对象存储或文档站点。

## 环境变量示例
参见项目根目录 `.env.example`，可复制为 `.env` 并按需修改 (Compose 会自动注入同名变量)。

## 搜索索引重建
当修改 ranking rules / 可搜索字段 / 需要批量修复时：
```
python -m scripts.reindex_search         # 仅已发布文章
python -m scripts.reindex_search --all   # 包含未发布
python -m scripts.reindex_search --skip-ranking  # 跳过 ranking rules 更新
```
Docker Compose 环境:
```
docker compose exec backend python -m scripts.reindex_search
```

Ranking Rules 默认顺序(如使用 MeiliSearch):
```
words, typo, proximity, attribute, sort, exactness, desc(likes_count), desc(views_count), desc(published_at)
```
可通过设置环境变量 `MEILI_SKIP_RANKING_RULES=1` 跳过自动更新（例如线上临时调试）。
