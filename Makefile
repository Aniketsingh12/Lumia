.PHONY: dev backend frontend widget install test lint clean deploy migrate seed

# Run backend + frontend (two terminals recommended)
dev:
	@echo "Run 'make backend' and 'make frontend' in separate terminals."
	@echo "Or on Windows, double-click start.bat."

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

widget:
	cd widget && npm run dev

worker:
	cd backend && celery -A app.tasks.celery_app worker --loglevel=info

# Setup
install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install
	cd widget && npm install

# Database
migrate:
	cd backend && python ../scripts/migrate.py

seed:
	cd backend && python ../scripts/seed_demo.py

# Testing
test:
	cd backend && pytest -v
	cd frontend && npm test

test-backend:
	cd backend && pytest -v

test-frontend:
	cd frontend && npm test

# Code quality
lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format

# Build
build-frontend:
	cd frontend && npm run build

build-widget:
	cd widget && npm run build

build: build-frontend build-widget

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist widget/dist

# Deploy
deploy:
	@echo "Frontend → Vercel (auto-deploys on git push)"
	@echo "Backend  → Render (auto-deploys on git push via render.yaml)"
	@echo "See docs/deploy-free.md"
