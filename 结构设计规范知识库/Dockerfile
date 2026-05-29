# ---- Builder ----
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements-runtime.txt .
RUN pip install --user --no-cache-dir -r requirements-runtime.txt

# ---- Runtime ----
FROM python:3.11-slim

WORKDIR /app

# 从 builder 复制已安装的包
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 创建数据目录
RUN mkdir -p /app/db /app/logs

# 复制应用代码
COPY src/ src/

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python3 -c "import http.client; c=http.client.HTTPConnection('localhost',8000); c.request('GET','/health'); r=c.getresponse(); assert r.status==200" || exit 1

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
