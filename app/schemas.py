from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict # === 🧠 Phase 2: Any, Dict 임포트 추가 ===

class TaskTicket(BaseModel):
    """파일 업로드 시 반환되는 작업 티켓 모델"""
    task_id: str

class TasksTicket(BaseModel):
    """여러 파일 업로드 시 반환되는 작업 티켓 리스트 모델"""
    task_ids: List[str]

class TaskStatus(BaseModel):
    """작업 상태 조회 시 반환되는 모델"""
    task_id: str
    status: str
    result: Optional[Any] = None # === 🧠 Phase 2: str -> Any로 변경 (JSON/Dict 반환) ===

class SearchHit(BaseModel):
    """MeiliSearch 검색 결과의 개별 항목 모델"""
    id: str
    filename: str
    content: str
    # === 🧠 Phase 2: MeiliSearch가 반환할 추가 필드 정의 ===
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
    detail: Optional[str] = None

class SemanticSearchHit(BaseModel):
    """Qdrant 검색 결과의 개별 항목 모델"""
    id: str         # Qdrant/MeiliSearch에서 공유하는 UUID
    score: float    # 코사인 유사도 점수
    filename: str
    doc_type: str
    summary: str

class SemanticSearchResult(BaseModel):
    """Qdrant 검색 결과 전체 응답 모델"""
    hits: List[SemanticSearchHit]
    query: str            # 사용자가 입력한 원본 쿼리
    processingTimeMs: float # 검색에 소요된 시간