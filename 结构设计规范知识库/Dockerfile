# syntax=docker/dockerfile:1@sha256:87999aa3d42bdc6bea60565083ee17e86d1f3339802f543c0d03998580f9cb89

# ---- Frontend builder ----
FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS frontend-builder

WORKDIR /app/frontend
COPY frontend/.npmrc frontend/package.json frontend/package-lock.json ./
RUN npm install --global npm@10.9.8
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/public/ public/
COPY frontend/src/ src/
RUN npm run build

# ---- Python dependency builder ----
FROM python:3.11-slim@sha256:9c900dea9e8fb7e16277c179b555cc72d29a352dbc33cff48ad5a0412fd5bfc7 AS python-builder

WORKDIR /app
COPY requirements-runtime.txt .
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-runtime.txt
RUN python -m pip check
RUN python -m pip uninstall --yes wheel setuptools pip

# ---- Runtime ----
FROM python:3.11-slim@sha256:9c900dea9e8fb7e16277c179b555cc72d29a352dbc33cff48ad5a0412fd5bfc7 AS runtime

WORKDIR /app

ARG APP_UID=10001
ARG APP_GID=10001

# 依赖只在 builder 安装；最终服务不保留包安装工具及其辅助包。
RUN python -m pip uninstall --yes jaraco.context wheel setuptools pip

# 从 builder 复制已检查且已移除安装工具的虚拟环境。
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 创建专用运行身份与可写数据目录。构建参数必须为正整数。
RUN case "$APP_UID" in ''|*[!0-9]*) \
      echo "APP_UID and APP_GID must be positive integers" >&2; exit 1 ;; esac \
    && case "$APP_GID" in ''|*[!0-9]*) \
      echo "APP_UID and APP_GID must be positive integers" >&2; exit 1 ;; esac \
    && if ! [ "$APP_UID" -gt 0 ] 2>/dev/null || ! [ "$APP_GID" -gt 0 ] 2>/dev/null; then \
      echo "APP_UID and APP_GID must be positive integers" >&2; exit 1; \
    fi \
    && groupadd --gid "$APP_GID" app \
    && useradd --uid "$APP_UID" --gid app --create-home --home-dir /home/app \
      --shell /usr/sbin/nologin app \
    && mkdir -p /app/db /app/logs /app/data \
    && chown -R app:app /app/db /app/logs /app/data

# 复制应用、控制台和运行时评估资产
COPY src/ src/
COPY --from=frontend-builder /app/frontend/dist frontend/dist/
COPY data/evaluation/ data/evaluation/
COPY data/metadata/ data/metadata/

USER app:app

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python3 -c "import http.client; c=http.client.HTTPConnection('localhost',8000); c.request('GET','/health'); r=c.getresponse(); assert r.status==200" || exit 1

EXPOSE 8000
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
