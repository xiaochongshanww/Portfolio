# Backend Dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# System deps (build for mysqlclient)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# 复制示例环境变量（生产部署应以实际机密覆盖）
COPY ../.env.example /app/.env.example

# Non-root user (optional)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
# alembic upgrade head then start gunicorn
CMD ["sh", "-c", "flask db upgrade && gunicorn -w 4 -b 0.0.0.0:8000 run:app"]

# 提供管理脚本 (reindex)
# 使用: docker compose exec backend python -m scripts.reindex_search
