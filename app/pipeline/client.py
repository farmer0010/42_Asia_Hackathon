# D:\42_asia-hackathon\app\pipeline\client.py (수정 완료된 전체 파일)

from __future__ import annotations
import os
import asyncio
from typing import Any, Dict, Optional

# --- 필요한 모든 클라이언트 라이브러리 ---
from openai import OpenAI, AsyncOpenAI
import meilisearch
from qdrant_client import QdrantClient
from qdrant_client.http import models

# 🔴 [수정] app.config에서 settings를 import합니다.
from app.config import settings


# -----------------------------------------------------------------
#   1. LLM 클라이언트 (Shimmy/OpenAI 호환)
# -----------------------------------------------------------------

def get_llm_client() -> OpenAI:
    """(동기용) LLM 클라이언트를 반환합니다."""
    # 🔴 [치명적 오류 수정 1]
    # .env와 연동되는 'LLM_API_BASE_URL' 변수를 사용해야 합니다.
    # (기존 코드 'LLM_BASE_URL'은 하드코딩된 기본값이었습니다)
    return OpenAI(
        base_url=settings.LLM_API_BASE_URL,
        api_key="EMPTY"
    )

def get_llm_aclient() -> AsyncOpenAI:
    """(비동기용) Async LLM 클라이언트를 반환합니다."""
    # 🔴 [치명적 오류 수정 1]
    # .env와 연동되는 'LLM_API_BASE_URL' 변수를 사용해야 합니다.
    return AsyncOpenAI(
        base_url=settings.LLM_API_BASE_URL,
        api_key="EMPTY"
    )

# -----------------------------------------------------------------
#   2. SearchClient (MeiliSearch) - 실제 구현
# -----------------------------------------------------------------

class SearchClient:
    """MeiliSearch 클라이언트 래퍼 (실제 구현)"""

    # 🔴 [치명적 오류 수정 2]
    # 생성자의 'api_key' 기본값을 settings.MEILI_MASTER_KEY로 변경합니다.
    # (기존 코드 'None'이 'invalid_api_key' 오류의 원인이었습니다)
    def __init__(self,
                 host_url: str = settings.MEILI_HOST_URL,
                 api_key: Optional[str] = settings.MEILI_MASTER_KEY): # ⬅️ 이 부분 수정
        try:
            # 🔴 이제 api_key=None이 아닌, settings에서 읽어온 키로 연결합니다.
            self.client = meilisearch.Client(host_url, api_key)
            self.index_name = "documents"  # 인덱스 이름 (고정)

            # (선택 사항) 키 전달 확인용 로그
            if api_key:
                print(f"[SearchClient] MeiliSearch 연결 성공 (호스트: {host_url}, API Key: ...{api_key[-4:]})")
            else:
                 print(f"[SearchClient] MeiliSearch 연결 성공 (호스트: {host_url}, API Key: None)")

        except Exception as e:
            print(f"[SearchClient] MeiliSearch 연결 실패: {e}")
            self.client = None

    def get_or_create_index(self):
        """(원본과 동일)"""
        if not self.client:
            raise Exception("MeiliSearch 클라이언트가 초기화되지 않았습니다.")

        try:
            # 인덱스가 이미 있는지 확인
            index = self.client.get_index(self.index_name)
            return index
        except Exception:
            # 없으면 생성 (primaryKey를 'document_id'로 설정)
            print(f"[SearchClient] '{self.index_name}' 인덱스를 생성합니다.")
            index = self.client.create_index(self.index_name, {'primaryKey': 'document_id'})
            return index

    def add_document(self, document_data: Dict[str, Any]):
        """(원본과 동일) 문서 1개를 MeiliSearch에 인덱싱합니다."""
        if not self.client:
            return None

        index = self.get_or_create_index()
        try:
            # document_id를 기준으로 추가 또는 업데이트
            print(f"[SearchClient] '{document_data.get('document_id')}' 인덱싱 시도...")
            response = index.add_documents([document_data], primary_key='document_id')
            print(f"[SearchClient] ...인덱싱 작업 요청 성공 (Task UID: {response.task_uid})")
            return response
        except Exception as e:
            print(f"[SearchClient] MeiliSearch 인덱싱 실패: {e}")
            return None


# -----------------------------------------------------------------
#   3. VectorClient (Qdrant) - 실제 구현
# -----------------------------------------------------------------

class VectorClient:
    """(원본과 동일) Qdrant 클라이언트 래퍼 (실제 구현)"""

    # Qdrant는 .env가 아닌 config.py의 기본값(qdrant:6333)을 사용하고 있으므로
    # 이 코드는 이미 올바르게 작동합니다. (수정 불필요)
    def __init__(self, host: str = settings.QDRANT_HOST, port: int = settings.QDRANT_PORT):
        self.host = host
        self.port = port
        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            self.collection_name = "document_chunks"  # 컬렉션 이름 (고정)
            self.vector_dim = settings.VECTOR_DIMENSION
            print(f"[VectorClient] Qdrant 연결 성공 (호스트: {self.host}:{self.port})")

            # 컬렉션이 없으면 생성
            self.get_or_create_collection()

        except Exception as e:
            print(f"[VectorClient] Qdrant 연결 실패: {e}")
            self.client = None

    def get_or_create_collection(self):
        """(원본과 동일)"""
        if not self.client:
            raise Exception("Qdrant 클라이언트가 초기화되지 않았습니다.")

        try:
            # 컬렉션 정보 조회 시도
            self.client.get_collection(collection_name=self.collection_name)
        except Exception as e:
            # 컬렉션이 존재하지 않으면 (e.g., "Not found" or 404) 새로 생성
            print(f"[VectorClient] '{self.collection_name}' 컬렉션을 생성합니다. (차원: {self.vector_dim})")
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_dim,
                    distance=models.Distance.COSINE  # 코사인 유사도 사용
                )
            )

    def add_vectors(self, points: list):
        """(원본과 동일) 포인트(벡터) 리스트를 Qdrant에 업로드합니다."""
        if not self.client or not points:
            return

        try:
            print(f"[VectorClient] {len(points)}개의 벡터 포인트 업로드 시도...")
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True  # 즉시 적용
            )
            print(f"[VectorClient] ...업로드 성공")
        except Exception as e:
            print(f"[VectorClient] Qdrant 업로드 실패: {e}")