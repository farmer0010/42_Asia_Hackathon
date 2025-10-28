import httpx
from typing import List

class LLMClient:
    def __init__(self, model="gemma3:4b", base="http://localhost:11434"):
        self.base = base
        self.model = model # (이것은 generate의 기본 모델이 됩니다)

    async def generate(self, prompt, max_tokens=800, temperature=0.0):
        async with httpx.AsyncClient(timeout=40) as cx:
            payload = {
                "model": self.model, # (생성용 모델 사용)
                "prompt": prompt,
                "options": {
                    "temperature": temperature,
                    "top_p": 1.0,
                    "num_ctx": 4096
                },
                "stream": False
            }
            r = await cx.post(f"{self.base}/api/generate", json=payload)
            r.raise_for_status()
            return r.json().get("response", "").strip()

    async def embed(self, text: str, embedding_model_name: str) -> List[float]:
        """텍스트 임베딩 (Ollama의 /api/embeddings 호출)"""
        async with httpx.AsyncClient(timeout=40) as cx:
            payload = {
                "model": embedding_model_name, # (임베딩용 모델 사용)
                "prompt": text
            }
            r = await cx.post(f"{self.base}/api/embeddings", json=payload)
            r.raise_for_status()
            # Ollama는 {'embedding': [0.1, 0.2, ...]} 형태를 반환.
            return r.json().get("embedding", [])