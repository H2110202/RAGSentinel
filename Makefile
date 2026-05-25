.PHONY: help dev dev-backend dev frontend init-db docker-up docker-down docker-logs clean

help:
	@echo "RAGSentinel - Available Commands"
	@echo "==============================="
	@echo "  make dev           Start both backend and frontend (dev mode)"
	@echo "  make dev-backend   Start backend only"
	@echo "  make dev-frontend  Start frontend only"
	@echo "  make init-db       Initialize database with default admin user"
	@echo "  make docker-up     Start all services via Docker Compose"
	@echo "  make docker-down   Stop all Docker services"
	@echo "  make docker-logs   Tail Docker service logs"
	@echo "  make clean         Remove generated files"

dev-backend:
	cd backend && pip install -r requirements.txt && python run.py

dev-frontend:
	cd frontend && node server.js

init-db:
	cd backend && python init_db.py

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/data/*.db 2>/dev/null || true
