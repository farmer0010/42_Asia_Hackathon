# 🐳 Docker 설정 최종 요약

## ✅ 수정 완료 사항

### 1. Dockerfile 수정

**이전 문제점:**
- ❌ 잘못된 디렉토리 참조 (`srcs/` → `src/`)
- ❌ 존재하지 않는 디렉토리 (`llm_service/`)
- ❌ 누락된 디렉토리 (`scripts/`, `config/`)
- ❌ OpenCV 의존성 누락

**수정 완료:**
- ✅ 올바른 디렉토리 구조 (`src/`, `scripts/`, `config/`, `tests/`)
- ✅ 완전한 시스템 의존성 (OpenCV, PaddleOCR 요구사항)
- ✅ 환경 변수 설정 (`PYTHONPATH`, `PYTHONUNBUFFERED`)
- ✅ 헬스체크 추가

### 2. Docker Compose 개선

**추가된 기능:**
- ✅ GPU 지원 (docker-compose.yml)
- ✅ CPU 모드 (docker-compose.cpu.yml)
- ✅ `USE_GPU` 환경 변수
- ✅ 자동 재시작 (`restart: unless-stopped`)
- ✅ 로그 로테이션 (10MB × 3개)
- ✅ Ollama 의존성 관리 (헬스체크 대기)

### 3. 새로운 파일

**`.dockerignore`**
- 불필요한 파일 제외 (venv, docs, 캐시 등)
- 빌드 속도 향상

**`docker/README.md`**
- 완전한 Docker 사용 가이드
- 문제 해결 섹션
- 커스터마이징 방법

**`docker/test-docker.sh`**
- 자동화된 Docker 설정 검증
- 10단계 테스트 프로세스

---

## 📁 최종 Docker 파일 구조

```
docker/
├── Dockerfile                  ✅ 수정 완료
├── docker-compose.yml         ✅ 개선 완료 (GPU)
├── docker-compose.cpu.yml     ✅ 개선 완료 (CPU)
├── README.md                  ✨ 새로 생성
└── test-docker.sh             ✨ 새로 생성

.dockerignore                  ✨ 새로 생성
```

---

## 🚀 빠른 시작 가이드

### 1. Docker 설정 테스트

```bash
# CPU 모드 테스트
cd docker
./test-docker.sh cpu

# GPU 모드 테스트 (NVIDIA GPU 서버)
./test-docker.sh gpu
```

### 2. 시스템 실행

**CPU 모드 (개발/로컬):**
```bash
cd docker
docker compose -f docker-compose.cpu.yml up --build
```

**GPU 모드 (프로덕션):**
```bash
cd docker
docker compose -f docker-compose.yml up --build -d
```

### 3. 로그 확인

```bash
# 전체 로그
docker compose logs -f

# Processor만
docker logs -f hackathon-processor

# Ollama만
docker logs -f hackathon-ollama
```

### 4. 종료

```bash
# CPU 모드
docker compose -f docker-compose.cpu.yml down

# GPU 모드
docker compose -f docker-compose.yml down
```

---

## 📊 Docker 구성 비교

| 항목 | GPU 모드 | CPU 모드 |
|------|----------|----------|
| **파일** | `docker-compose.yml` | `docker-compose.cpu.yml` |
| **Ollama GPU** | ✅ NVIDIA GPU | ❌ CPU only |
| **Processor GPU** | ✅ NVIDIA GPU | ❌ CPU only |
| **환경 변수** | `USE_GPU=true` | `USE_GPU=false` |
| **속도** | 3-5배 빠름 | 기본 속도 |
| **메모리** | 12-16GB | 8-12GB |
| **권장 환경** | 프로덕션, GPU 서버 | 개발, 테스트, M1 Mac |

---

## 🔧 주요 수정 사항 상세

### Dockerfile

**변경 전:**
```dockerfile
COPY srcs/ ./srcs/           # ❌
COPY llm_service/ ./llm_service/  # ❌
COPY run_pipeline.sh .       # ❌
```

**변경 후:**
```dockerfile
COPY src/ ./src/             # ✅
COPY scripts/ ./scripts/     # ✅
COPY config/ ./config/       # ✅
COPY tests/ ./tests/         # ✅
```

### 시스템 의존성 추가

```dockerfile
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \      # OpenCV 필수
    libglib2.0-0 \         # 시스템 라이브러리
    libsm6 \               # X11
    libxext6 \             # X11
    libxrender-dev \       # 렌더링
    libgomp1 \             # OpenMP
    curl \                 # 유틸리티
    git                    # Git
```

### 환경 변수

```dockerfile
ENV PYTHONPATH=/app              # Python import 경로
ENV PYTHONUNBUFFERED=1           # 즉시 로그 출력
```

---

## 🎯 사용 시나리오

### 시나리오 1: 로컬 개발 (MacBook M1/M2)

```bash
# CPU 모드 사용
cd docker
docker compose -f docker-compose.cpu.yml up

# 코드 수정 후 재빌드
docker compose -f docker-compose.cpu.yml up --build

# 특정 테스트 실행
docker exec -it hackathon-processor \
  python tests/test_final_integration.py
```

### 시나리오 2: GPU 서버 배포 (태국 해커톤)

```bash
# 백그라운드 실행
cd docker
docker compose -f docker-compose.yml up -d

# 실시간 로그
docker logs -f hackathon-processor

# 상태 확인
docker compose ps

# 리소스 모니터링
docker stats
```

### 시나리오 3: 배치 처리

```bash
# 1. 입력 이미지 준비
cp ~/documents/*.jpg data/input/

# 2. 처리 시작
cd docker
docker compose -f docker-compose.cpu.yml up

# 3. 결과 확인
ls -la ../data/output/

# 4. 정리
docker compose -f docker-compose.cpu.yml down
```

---

## 🧪 테스트 결과 예상 출력

### test-docker.sh 실행 시

```
==================================
🐳 Docker 설정 테스트
==================================
모드: cpu
파일: docker-compose.cpu.yml

1️⃣  Docker 설치 확인...
✅ Docker 버전: Docker version 24.0.6

2️⃣  Docker Compose 설치 확인...
✅ Docker Compose 버전: Docker Compose version v2.21.0

4️⃣  필수 디렉토리 확인...
✅ data/input 존재
✅ data/output 존재
✅ data/models 존재
✅ src 존재
✅ scripts 존재
✅ config 존재

5️⃣  Dockerfile 검증...
✅ Dockerfile 존재

6️⃣  docker-compose 파일 검증...
✅ docker-compose.cpu.yml 존재

7️⃣  설정 검증...
✅ Docker Compose 설정 유효

8️⃣  이미지 빌드 테스트...
   (이 과정은 몇 분 소요됩니다...)
✅ 이미지 빌드 성공

9️⃣  이미지 크기 확인...
   이미지 크기: 2.5 GB

==================================
✅ 모든 테스트 통과!
==================================

🚀 다음 명령어로 시스템을 시작할 수 있습니다:

   docker compose -f docker-compose.cpu.yml up
```

---

## 🔍 검증 체크리스트

배포 전 확인사항:

### 시스템 요구사항
- [ ] Docker 24.0+ 설치
- [ ] Docker Compose 2.0+ 설치
- [ ] 디스크 여유 공간 20GB+
- [ ] RAM 8GB+ (권장 16GB)
- [ ] GPU 모드: NVIDIA Container Toolkit

### 프로젝트 구조
- [ ] `src/` 디렉토리 존재
- [ ] `scripts/` 디렉토리 존재
- [ ] `config/` 디렉토리 존재
- [ ] `data/input/` 디렉토리 존재
- [ ] `data/output/` 디렉토리 존재
- [ ] `data/models/` 디렉토리 존재
- [ ] `requirements.txt` 파일 존재

### Docker 파일
- [ ] `docker/Dockerfile` 정상
- [ ] `docker/docker-compose.yml` 정상
- [ ] `docker/docker-compose.cpu.yml` 정상
- [ ] `.dockerignore` 존재

### 테스트
- [ ] `./docker/test-docker.sh cpu` 통과
- [ ] 이미지 빌드 성공
- [ ] 컨테이너 시작 성공
- [ ] Ollama 헬스체크 통과

---

## 🐛 알려진 문제 및 해결

### 1. "Cannot connect to Ollama"

**원인**: Ollama가 완전히 시작되지 않음

**해결**:
```bash
# Ollama 로그 확인
docker logs hackathon-ollama

# 대기 시간 증가 (docker-compose.yml)
sleep 10 → sleep 20
```

### 2. 빌드 시 메모리 부족

**해결**:
```bash
# Docker Desktop 메모리 할당 증가 (설정 → Resources)
# 또는 스왑 메모리 활성화
```

### 3. GPU 인식 안 됨

**해결**:
```bash
# NVIDIA Container Toolkit 설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 4. M1 Mac에서 GPU 모드 시도 시

**증상**: GPU 모드가 작동하지 않음

**해결**: CPU 모드 사용
```bash
docker compose -f docker-compose.cpu.yml up
```

---

## 📚 추가 리소스

### 문서
- [Docker 완전 가이드](docker/README.md)
- [프로젝트 완전체 가이드](docs/COMPLETE_GUIDE.md)
- [다국어 지원 가이드](docs/MULTILINGUAL_GUIDE.md)

### 유용한 명령어

```bash
# 이미지 정리
docker image prune -a

# 볼륨 정리
docker volume prune

# 전체 정리 (주의!)
docker system prune -a --volumes

# 컨테이너 재시작
docker compose restart processor

# 로그 저장
docker logs hackathon-processor > processor.log 2>&1
```

---

## 🎉 결론

### ✅ 완료된 작업

1. **Dockerfile 완전 수정** - 올바른 경로와 의존성
2. **Docker Compose 개선** - GPU/CPU 모드 분리
3. **문서화** - 완전한 사용 가이드
4. **자동화 테스트** - test-docker.sh 스크립트
5. **.dockerignore** - 빌드 최적화

### 🚀 준비 완료

Docker 설정이 완벽하게 구성되었습니다!

**다음 단계:**

```bash
# 1. 설정 테스트
cd docker && ./test-docker.sh cpu

# 2. 시스템 시작
docker compose -f docker-compose.cpu.yml up --build

# 3. 결과 확인
docker logs -f hackathon-processor
```

---

**Happy Hacking with Docker! 🐳**

*Last Updated: 2024-11-06*

