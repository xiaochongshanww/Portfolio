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
FROM python:3.11-slim@sha256:90744cff8f32887f075c47d747a173ff333e9e98801667af93c357fa9f5e28ff AS python-builder

WORKDIR /app
COPY requirements-runtime.txt .
RUN pip install --user --no-cache-dir --require-hashes -r requirements-runtime.txt
RUN python -m pip check

# ---- Runtime ----
FROM python:3.11-slim@sha256:90744cff8f32887f075c47d747a173ff333e9e98801667af93c357fa9f5e28ff AS runtime

WORKDIR /app

# 依赖只在 builder 安装；最终服务不保留包安装工具及其辅助包。
RUN python -m pip uninstall --yes jaraco.context wheel setuptools pip

# 从 builder 复制已安装的包
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 创建数据目录
RUN mkdir -p /app/db /app/logs /app/data

# 复制应用、控制台和运行时评估资产
COPY src/ src/
COPY --from=frontend-builder /app/frontend/dist frontend/dist/
COPY data/evaluation/ data/evaluation/
COPY data/metadata/ data/metadata/

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python3 -c "import http.client; c=http.client.HTTPConnection('localhost',8000); c.request('GET','/health'); r=c.getresponse(); assert r.status==200" || exit 1

EXPOSE 8000
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
