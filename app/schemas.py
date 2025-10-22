from pydantic import BaseModel, Field
from typing import List, Optional, Any

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
    result: Optional[str] = None

class SearchHit(BaseModel):
    """MeiliSearch 검색 결과의 개별 항목 모델"""
    id: str
    filename: str
    content: str

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