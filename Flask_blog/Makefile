# ============================================================
# Flask Blog 测试与开发命令
# ============================================================

.PHONY: test test-backend test-frontend test-all lint format setup clean

# ─── 测试 ──────────────────────────────────────────────────

test-backend:
	cd backend && python -m pytest -q --tb=short

test-backend-cov:
	cd backend && python -m pytest --cov=app --cov-report=term-missing --cov-report=html

test-backend-v:
	cd backend && python -m pytest -v --tb=long

test-frontend:
	cd frontend && npx vitest run

test-frontend-ui:
	cd frontend && npx vitest --ui

test-frontend-cov:
	cd frontend && npx vitest run --coverage

test-e2e:
	npx playwright test

test: test-backend test-frontend

test-all: test-backend-cov test-frontend-cov

# ─── Lint ──────────────────────────────────────────────────

lint:
	cd backend && flake8 app/ tests/ --exit-zero
	cd backend && black --check app/ tests/
	cd frontend && npx eslint src

format:
	cd backend && isort app/ tests/
	cd backend && black app/ tests/
	cd frontend && npx prettier --write src/

# ─── 环境 ──────────────────────────────────────────────────

setup:
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm install

db-upgrade:
	cd backend && flask db upgrade

dev:
	cd backend && flask run &

# ─── 清理 ──────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov frontend/dist
