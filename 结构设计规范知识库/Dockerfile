# syntax=docker/dockerfile:1@sha256:87999aa3d42bdc6bea60565083ee17e86d1f3339802f543c0d03998580f9cb89

# ---- Frontend builder ----
FROM node:26-alpine@sha256:aadf416b2cdce311a8811ba3f0608a61b77dbf997500e2eafe781b51f6a0b019 AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --global npm@10.9.8
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Python dependency builder ----
FROM python:3.11-slim@sha256:90744cff8f32887f075c47d747a173ff333e9e98801667af93c357fa9f5e28ff AS python-builder

WORKDIR /app
COPY requirements-runtime.txt .
RUN pip install --user --no-cache-dir --require-hashes -r requirements-runtime.txt

# ---- Runtime ----
FROM python:3.11-slim@sha256:90744cff8f32887f075c47d747a173ff333e9e98801667af93c357fa9f5e28ff AS runtime

WORKDIR /app

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
