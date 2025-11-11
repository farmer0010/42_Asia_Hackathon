.PHONY: help build up down logs clean rebuild restart

# 기본 타겟
help:
	@echo "=========================================="
	@echo "42 Asia Hackathon - Document Processor"
	@echo "=========================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make build    - Docker 이미지 빌드 (models 포함)"
	@echo "  make up       - 서비스 시작"
	@echo "  make down     - 서비스 중지"
	@echo "  make logs     - 로그 확인"
	@echo "  make restart  - 서비스 재시작"
	@echo "  make rebuild  - 이미지 재빌드 후 시작"
	@echo "  make clean    - 모든 컨테이너/볼륨 삭제"
	@echo ""

# Docker 이미지 빌드
build:
	@echo "Building Docker images (including 1.1GB models)..."
	cd docker && docker compose build

# 서비스 시작
up:
	@echo "Starting services..."
	cd docker && docker compose up -d
	@echo ""
	@echo "Services started! Check logs with: make logs"

# 서비스 중지
down:
	@echo "Stopping services..."
	cd docker && docker compose down

# 로그 확인
logs:
	cd docker && docker compose logs -f

# 서비스 재시작
restart: down up

# 재빌드 후 시작
rebuild:
	@echo "Rebuilding and starting..."
	cd docker && docker compose up -d --build

# 완전 정리
clean:
	@echo "Cleaning up all containers and volumes..."
	cd docker && docker compose down -v
	@echo "Cleanup complete!"

