# D:\42_asia-hackathon\app\schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# 🚨 [수정 5]: main.py와 이름 통일
class UploadResponse(BaseModel):
    """파일 업로드 시 반환되는 작업 티켓 모델"""
    job_id: str
    filename: str
    message: str = "File received and processing started."

class JobStatusResponse(BaseModel):
    """작업 상태 조회 시 반환되는 모델"""
    job_id: str
    status: str
    message: Optional[str] = None
    result: Optional[Any] = None # JSON/Dict 결과

# --- (기존 검색 모델) ---
class SearchResponse(BaseModel):
    hits: List[Dict[str, Any]]

class SearchHit(BaseModel):
    id: str
    filename: str
    content: str
    doc_type: Optional[str] = None
    doc_confidence: Optional[float] = None
    summary: Optional[str] = None
    pii_count: Optional[int] = None
    extracted_data: Optional[Dict] = None

class SearchResult(BaseModel):
    hits: List[SearchHit]
    query: str
    processingTimeMs: int
    limit: int
    offset: int
    estimatedTotalHits: int

class HealthCheck(BaseModel):
    status: str
    services: Dict[str, Any]

class SemanticSearchHit(BaseModel):
    id: str
    score: float
    filename: str
    doc_type: str
    summary: str

class SemanticSearchResult(BaseModel):
    hits: List[SemanticSearchHit]
    query: str
    processingTimeMs: float