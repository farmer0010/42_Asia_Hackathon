# 🐳 Docker 배포 가이드

## 📋 개요

이 프로젝트는 Docker와 Docker Compose를 사용하여 완전한 문서 처리 시스템을 컨테이너화합니다.

### 포함된 서비스

1. **Ollama LLM 서비스** - Qwen2.5 모델 자동 로드
2. **문서 처리 프로세서** - OCR, 분류, 추출, 요약, PII 처리

---

## 🚀 빠른 시작

### CPU 모드 (개발/테스트)

```bash
# 1. Docker 디렉토리로 이동
cd docker/

# 2. CPU 모드로 실행
docker compose -f docker-compose.cpu.yml up --build

# 3. 로그 확인
docker logs -f hackathon-processor
```

### GPU 모드 (프로덕션)

```bash
# NVIDIA GPU 서버에서만 실행 가능

# 1. Docker 디렉토리로 이동
cd docker/

# 2. GPU 모드로 실행
docker compose -f docker-compose.yml up --build

# 3. 로그 확인
docker logs -f hackathon-processor
```

---

## 📦 파일 구조

```
docker/
├── Dockerfile                  # 메인 이미지 정의
├── docker-compose.yml         # GPU 모드 구성
├── docker-compose.cpu.yml     # CPU 모드 구성
└── README.md                  # 이 파일
```

---

## 🔧 Dockerfile 상세

### 베이스 이미지
- **Python 3.11-slim**: 경량 Python 이미지

### 시스템 의존성
```dockerfile
libgl1-mesa-glx    # OpenCV
libglib2.0-0       # 시스템 라이브러리
libsm6, libxext6   # X11 관련
libxrender-dev     # 렌더링
libgomp1           # OpenMP
curl, git          # 유틸리티
```

### 프로젝트 파일
- `src/` - 소스 코드
- `scripts/` - 실행 스크립트
- `config/` - 설정 파일
- `tests/` - 테스트 파일 (선택)

### 환경 변수
- `PYTHONPATH=/app` - Python 경로
- `PYTHONUNBUFFERED=1` - 즉시 로그 출력

---

## 📝 Docker Compose 구성

### 공통 설정

**Ollama 서비스:**
- 포트: `11434`
- 자동 모델 다운로드: `qwen2.5:7b`
- 헬스체크: 10초마다 확인

**Processor 서비스:**
- 의존성: Ollama 헬스체크 통과 후 시작
- 볼륨 마운트:
  - `../data/input` → `/app/data/input`
  - `../data/output` → `/app/data/output`
  - `../data/models` → `/app/data/models`
- 재시작 정책: `unless-stopped`
- 로그 로테이션: 10MB × 3개 파일

### GPU vs CPU 차이

| 구성 | GPU 모드 | CPU 모드 |
|------|----------|----------|
| Ollama GPU | ✅ | ❌ |
| Processor GPU | ✅ | ❌ |
| `USE_GPU` 환경 변수 | `true` | `false` |
| 성능 | 3-5배 빠름 | 기본 속도 |

---

## 🎯 사용 시나리오

### 시나리오 1: 로컬 개발

```bash
# CPU 모드로 개발
docker compose -f docker/docker-compose.cpu.yml up

# 코드 수정 후 재빌드
docker compose -f docker/docker-compose.cpu.yml up --build

# 종료
docker compose -f docker/docker-compose.cpu.yml down
```

### 시나리오 2: 프로덕션 배포 (GPU 서버)

```bash
# 백그라운드 실행
docker compose -f docker/docker-compose.yml up -d

# 로그 스트리밍
docker logs -f hackathon-processor

# 상태 확인
docker compose ps

# 정지
docker compose -f docker/docker-compose.yml down
```

### 시나리오 3: 배치 처리

```bash
# 1. 입력 파일 준비
cp my_documents/*.jpg data/input/

# 2. 컨테이너 시작
docker compose -f docker/docker-compose.cpu.yml up

# 3. 처리 완료 대기 (로그 확인)

# 4. 결과 확인
ls -la data/output/

# 5. 컨테이너 정지
docker compose -f docker/docker-compose.cpu.yml down
```

---

## 🔍 디버깅

### 컨테이너 접속

```bash
# Processor 컨테이너 접속
docker exec -it hackathon-processor bash

# 내부에서 명령 실행
python tests/test_final_integration.py
```

### 로그 확인

```bash
# 전체 로그
docker compose logs

# 특정 서비스 로그
docker logs hackathon-processor
docker logs hackathon-ollama

# 실시간 로그
docker logs -f hackathon-processor
```

### 볼륨 확인

```bash
# 볼륨 리스트
docker volume ls

# Ollama 모델 볼륨 확인
docker volume inspect docker_ollama_models
```

---

## ⚙️ 커스터마이징

### 1. 다른 Ollama 모델 사용

**docker-compose.yml 수정:**
```yaml
command: >
  "ollama serve &
   OLLAMA_PID=$$!
   sleep 10
   ollama pull qwen2.5:3b  # ← 여기 수정 (더 작은 모델)
   wait $$OLLAMA_PID"
```

### 2. GPU 개수 조정

**docker-compose.yml 수정:**
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 2  # ← GPU 2개 사용
          capabilities: [gpu]
```

### 3. 메모리 제한

**docker-compose.yml에 추가:**
```yaml
processor:
  # ... 기존 설정 ...
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
```

### 4. 환경 변수 추가

**.env 파일 생성:**
```bash
# docker/.env
OLLAMA_URL=http://ollama:11434
USE_GPU=false
OCR_LANGUAGES=en,korean,japan,thai
ENABLE_HANDWRITING=true
```

**docker-compose.yml에서 사용:**
```yaml
processor:
  env_file:
    - .env
```

---

## 🧪 테스트

### Docker 빌드 테스트

```bash
# 이미지만 빌드 (실행 안 함)
docker build -t doc-processor -f docker/Dockerfile ..

# 빌드 성공 확인
docker images | grep doc-processor
```

### 컨테이너 테스트

```bash
# 단독 실행
docker run --rm -v $(pwd)/data:/app/data doc-processor \
  python tests/test_final_integration.py

# 결과 확인
echo $?  # 0이면 성공
```

---

## 📊 성능 모니터링

### 리소스 사용량 확인

```bash
# 실시간 모니터링
docker stats

# 특정 컨테이너
docker stats hackathon-processor
```

### 디스크 사용량

```bash
# 이미지 크기
docker images | grep doc-processor

# 볼륨 크기
docker system df -v
```

---

## 🛠️ 문제 해결

### 문제 1: "Cannot connect to Ollama"

**원인**: Ollama 서비스가 아직 준비되지 않음

**해결책**:
```bash
# Ollama 로그 확인
docker logs hackathon-ollama

# 헬스체크 상태 확인
docker compose ps

# 충분한 대기 시간 후 재시도
```

### 문제 2: GPU가 인식되지 않음

**원인**: NVIDIA Container Toolkit 미설치

**해결책**:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 문제 3: 메모리 부족

**원인**: 모든 OCR 언어 모델이 동시 로드됨

**해결책**:
```bash
# 메모리 제한 설정
docker compose -f docker-compose.cpu.yml up --scale processor=1 \
  --memory=8g
```

### 문제 4: 빌드가 느림

**해결책**:
```bash
# 빌드 캐시 사용
docker compose build --no-cache processor  # 캐시 무시 (필요 시)

# BuildKit 활성화 (더 빠른 빌드)
export DOCKER_BUILDKIT=1
docker compose build
```

---

## 🔒 보안 고려사항

### 1. 프로덕션 배포 시

- **환경 변수 보호**: `.env` 파일 사용, Git에 커밋 금지
- **네트워크 격리**: 외부 접근 제한
- **볼륨 권한**: 읽기 전용 마운트 고려

```yaml
volumes:
  - ../data/input:/app/data/input:ro  # 읽기 전용
```

### 2. 이미지 최적화

```dockerfile
# 멀티스테이지 빌드 (선택)
FROM python:3.11-slim as builder
# ... 빌드 단계 ...

FROM python:3.11-slim
# ... 최종 이미지 ...
```

---

## 📚 추가 리소스

### 공식 문서
- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 가이드](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)

### 관련 문서
- [프로젝트 완전체 가이드](../docs/COMPLETE_GUIDE.md)
- [다국어 지원 가이드](../docs/MULTILINGUAL_GUIDE.md)

---

## ✅ 체크리스트

배포 전 확인사항:

- [ ] Docker 및 Docker Compose 설치 확인
- [ ] GPU 사용 시 NVIDIA Container Toolkit 설치
- [ ] `data/input/` 디렉토리에 테스트 이미지 준비
- [ ] `data/models/` 디렉토리에 학습된 분류기 모델 준비 (선택)
- [ ] 충분한 디스크 공간 (최소 20GB)
- [ ] 충분한 메모리 (최소 8GB, 권장 16GB)

---

## 🎉 요약

### 빠른 시작 명령어

```bash
# CPU 모드 (개발/테스트)
cd docker && docker compose -f docker-compose.cpu.yml up --build

# GPU 모드 (프로덕션)
cd docker && docker compose -f docker-compose.yml up --build -d
```

### 주요 엔드포인트

- **Ollama LLM**: http://localhost:11434
- **입력 폴더**: `data/input/`
- **출력 폴더**: `data/output/`
- **모델 폴더**: `data/models/`

---

**Happy Dockerizing! 🐳**

*Last Updated: 2024-11-06*

