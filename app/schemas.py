# [수정 후: app/schemas.py]
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# 1. 파일 업로드 응답 (변경 없음)
class UploadResponse(BaseModel):
    """파일 업로드 시 반환되는 작업 티켓 모델"""
    job_id: str  # main.py의 /uploadfile/이 job_id를 반환
    filename: str
    message: str = "File received and processing started."


# 2. 🟢 [스키마 수정] JobStatusResponse -> TaskStatusResponse
class TaskStatusResponse(BaseModel):
    """작업 상태 조회 시 반환되는 모델 (main.py /tasks/{task_id}와 일치)"""
    task_id: str # main.py가 task_id를 사용
    status: str
    result: Optional[Any] = None  # 성공 시 PipelineResult, 실패 시 {"error": "..."}


# 3. 🟢 [스키마 수정] /search가 반환하는 검색 결과의 단일 항목
# (main.py 153, 172 라인에서 이 구조를 사용)
class SearchHit(BaseModel):
    document_id: str
    filename: str
    doc_type: Optional[str] = None
    snippet: str


# 4. 🟢 [스키마 수정] /search API의 최종 응답 모델
# (main.py 140, 178 라인에서 이 구조를 반환)
class SearchResponse(BaseModel):
    exact_matches: List[SearchHit]
    semantic_matches: List[SearchHit]


# 5. 헬스 체크 (변경 없음)
class HealthCheck(BaseModel):
    status: str
    services: Dict[str, Any]

# --- (기존 SearchResult, SemanticSearchHit 등은 /search API가 사용하지 않으므로 삭제) ---