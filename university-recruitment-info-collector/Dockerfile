FROM python:3.11-slim

WORKDIR /app

# Install system deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libgbm1 libdrm2 \
    libxkbcommon0 libxdamage1 libpango-1.0-0 libcairo2 libasound2 \
    libnss3 libnspr4 libxshmfence1 libcups2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir . && pip install --no-cache-dir playwright uvicorn

# Install Playwright browsers
RUN python3 -m playwright install chromium

# Copy source
COPY src/ src/
COPY config/ config/
COPY data/ data/
COPY .env ./

# Frontend build
COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm install && npm install tailwindcss postcss autoprefixer
COPY frontend/ frontend/
RUN cd frontend && npx vite build

# Expose
EXPOSE 8001

# Start
CMD ["uvicorn", "university_recruitment.user_portal.api:app", "--host", "0.0.0.0", "--port", "8001"]
