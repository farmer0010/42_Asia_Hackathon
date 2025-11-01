import httpx
from typing import List
from openai import OpenAI, AsyncOpenAI # ◀ openai 라이브러리 사용
from ..config import get_settings # ◀ 한 단계 상위 폴더의 config 임포트
import logging

log = logging.getLogger(__name__)
settings = get_settings()

# Shimmy가 OpenAI API와 호환되므로 OpenAI 클라이언트를 사용합니다.
async_client = AsyncOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key="shimmy", # shimmy는 API 키가 필요 없으므로 아무 값이나 넣습니다.
    timeout=40
)

class LLMClient:
    def __init__(self, model="gemma3:4b", base="http://localhost:11434"):
        # config.py에서 전역 클라이언트와 모델명을 가져와 사용합니다.
        self.model = settings.LLM_MODEL_NAME
        self.client = async_client

    async def generate(self, prompt, max_tokens=800, temperature=0.0):
        try:
            log.info(f"LLM generate 호출: {self.model}")
            completion = await self.client.chat.completions.create(
                model=self.model, # (GGUF 파일명)
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"LLM generate 실패: {e}", exc_info=True)
            return ""

    async def embed(self, text: str, embedding_model_name: str) -> List[float]:
        """텍스트 임베딩 (OpenAI 호환 /v1/embeddings 호출)"""
        try:
            log.info(f"LLM embed 호출: {embedding_model_name}")
            embedding_response = await self.client.embeddings.create(
                model=embedding_model_name, # (Safetensors 파일명)
                input=text
            )
            return embedding_response.data[0].embedding
        except Exception as e:
            log.error(f"LLM embed 실패: {e}", exc_info=True)
            return []