# D:\42_asia_hackathon\app\schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# --- API 응답 모델 ---

class UploadResponse(BaseModel):  # 🚨 [수정 1]: TaskTicket -> UploadResponse로 이름 변경
    """파일 업로드 시 반환되는 작업 티켓 모델"""
    job_id: str
    filename: str = Field(..., description="업로드된 파일 이름")
    message: str = "File received and processing started."

class UploadsResponse(BaseModel): # TasksTicket -> UploadsResponse로 이름 변경
    """여러 파일 업로드 시 반환되는 작업 티켓 리스트 모델"""
    job_ids: List[str]

class JobStatusResponse(BaseModel): # 🚨 [수정 2]: TaskStatus -> JobStatusResponse로 이름 변경
    """작업 상태 조회 시 반환되는 모델"""
    job_id: str = Field(..., description="Celery 작업 ID")
    status: str
    message: Optional[str] = None
    result: Optional[Any] = None # JSON 결과가 담깁니다.

# --- 검색 모델 ---

class SearchHit(BaseModel):
    """MeiliSearch 검색 결과의 개별 항목 모델"""
    id: str
    filename: str
    content: str
    doc_type: Optional[str] = None
    doc_confidence: Optional[float] = None
    summary: Optional[str] = None
    pii_count: Optional[int] = None
    extracted_data: Optional[Dict] = None

class SearchResult(BaseModel):
    """MeiliSearch 검색 결과 전체 응답 모델"""
    hits: List[SearchHit]
    query: str
    processingTimeMs: int
    limit: int
    offset: int
    estimatedTotalHits: int

class HealthCheck(BaseModel):
    """헬스 체크 응답 모델"""
    status: str
    services: Dict[str, Any]

class SemanticSearchHit(BaseModel):
    """Qdrant 검색 결과의 개별 항목 모델"""
    id: str
    score: float
    filename: str
    doc_type: str
    summary: str

class SemanticSearchResult(BaseModel):
    """Qdrant 검색 결과 전체 응답 모델"""
    hits: List[SemanticSearchHit]
    query: str
    processingTimeMs: float