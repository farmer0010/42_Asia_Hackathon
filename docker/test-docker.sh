#!/bin/bash

# Docker 설정 테스트 스크립트
# 사용법: ./test-docker.sh [cpu|gpu]

set -e

MODE=${1:-cpu}
COMPOSE_FILE="docker-compose.cpu.yml"

if [ "$MODE" = "gpu" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

echo "=================================="
echo "🐳 Docker 설정 테스트"
echo "=================================="
echo "모드: $MODE"
echo "파일: $COMPOSE_FILE"
echo ""

# 1. Docker 설치 확인
echo "1️⃣  Docker 설치 확인..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다."
    exit 1
fi
echo "✅ Docker 버전: $(docker --version)"

# 2. Docker Compose 설치 확인
echo ""
echo "2️⃣  Docker Compose 설치 확인..."
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose가 설치되지 않았습니다."
    exit 1
fi
echo "✅ Docker Compose 버전: $(docker compose version)"

# 3. GPU 모드일 경우 NVIDIA 확인
if [ "$MODE" = "gpu" ]; then
    echo ""
    echo "3️⃣  NVIDIA GPU 확인..."
    if ! command -v nvidia-smi &> /dev/null; then
        echo "⚠️  nvidia-smi를 찾을 수 없습니다. GPU 모드는 NVIDIA GPU가 필요합니다."
    else
        echo "✅ GPU 정보:"
        nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    fi
fi

# 4. 필수 디렉토리 확인
echo ""
echo "4️⃣  필수 디렉토리 확인..."
cd ..
for dir in data/input data/output data/models src scripts config; do
    if [ ! -d "$dir" ]; then
        echo "❌ $dir 디렉토리가 없습니다."
        exit 1
    fi
    echo "✅ $dir 존재"
done

# 5. Dockerfile 검증
echo ""
echo "5️⃣  Dockerfile 검증..."
if [ ! -f "docker/Dockerfile" ]; then
    echo "❌ docker/Dockerfile이 없습니다."
    exit 1
fi
echo "✅ Dockerfile 존재"

# 6. docker-compose 파일 검증
echo ""
echo "6️⃣  docker-compose 파일 검증..."
if [ ! -f "docker/$COMPOSE_FILE" ]; then
    echo "❌ docker/$COMPOSE_FILE이 없습니다."
    exit 1
fi
echo "✅ $COMPOSE_FILE 존재"

# 7. 설정 검증 (docker compose config)
echo ""
echo "7️⃣  설정 검증..."
cd docker
if docker compose -f $COMPOSE_FILE config > /dev/null 2>&1; then
    echo "✅ Docker Compose 설정 유효"
else
    echo "❌ Docker Compose 설정 오류"
    docker compose -f $COMPOSE_FILE config
    exit 1
fi

# 8. 이미지 빌드 테스트
echo ""
echo "8️⃣  이미지 빌드 테스트..."
echo "   (이 과정은 몇 분 소요됩니다...)"
if docker compose -f $COMPOSE_FILE build > /tmp/docker-build.log 2>&1; then
    echo "✅ 이미지 빌드 성공"
else
    echo "❌ 이미지 빌드 실패"
    cat /tmp/docker-build.log
    exit 1
fi

# 9. 이미지 크기 확인
echo ""
echo "9️⃣  이미지 크기 확인..."
IMAGE_SIZE=$(docker images | grep "docker-processor" | awk '{print $7" "$8}' | head -1)
if [ -z "$IMAGE_SIZE" ]; then
    IMAGE_SIZE=$(docker images | grep "42_asia_hackathon" | awk '{print $7" "$8}' | head -1)
fi
echo "   이미지 크기: $IMAGE_SIZE"

# 10. 요약
echo ""
echo "=================================="
echo "✅ 모든 테스트 통과!"
echo "=================================="
echo ""
echo "🚀 다음 명령어로 시스템을 시작할 수 있습니다:"
echo ""
if [ "$MODE" = "cpu" ]; then
    echo "   docker compose -f docker-compose.cpu.yml up"
else
    echo "   docker compose -f docker-compose.yml up"
fi
echo ""
echo "📝 로그 확인:"
echo "   docker logs -f hackathon-processor"
echo ""
echo "🛑 종료:"
if [ "$MODE" = "cpu" ]; then
    echo "   docker compose -f docker-compose.cpu.yml down"
else
    echo "   docker compose -f docker-compose.yml down"
fi
echo ""

