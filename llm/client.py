# llm/client.py
from __future__ import annotations
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
import httpx
from typing import Any, Dict, Optional


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _int_from_env(name: str, default: int) -> int:
    try:
        v = os.getenv(name)
        return int(v) if v is not None else default
    except Exception:
        return default


class LLMClient:
    """
    - OLLAMA_HOST 환경변수를 최우선 사용 (예: http://ollama:11434)
    - 기본값은 docker-compose 서비스 DNS 'http://ollama:11434'
    - generate():
        * Ollama 준비상태 폴링 (api/tags)
        * 넉넉한 timeout (CPU-only 환경 고려)
        * 지수 백오프 재시도
        * num_ctx / num_predict 을 ENV로 조절 가능
          - OLLAMA_NUM_CTX (기본 2048)
          - OLLAMA_NUM_PREDICT (기본 128)  # 필요 시 커스터마이즈
          - OLLAMA_TIMEOUT_SEC (기본 600)
    - save_real_outputs(): 결과를 호스트의 real_outputs/ (볼륨 마운트)로 저장
    """
    def __init__(self, model: str = "gemma3:4b", base: Optional[str] = None) -> None:
        base_env = os.environ.get("OLLAMA_HOST")  # docker-compose에서 주입됨
        self.base = (base or base_env or "http://ollama:11434").rstrip("/")
        self.model = model

        # CPU-only 환경에서 합리적 기본값 (필요시 ENV로 조정)
        self.num_ctx = _int_from_env("OLLAMA_NUM_CTX", 2048)
        self.num_predict_default = _int_from_env("OLLAMA_NUM_PREDICT", 128)

        # connect/read/write/pool 모두 넉넉히
        self.timeout_sec = _int_from_env("OLLAMA_TIMEOUT_SEC", 600)
        self._timeout = httpx.Timeout(
            connect=10.0,
            read=float(self.timeout_sec),
            write=float(self.timeout_sec),
            pool=float(self.timeout_sec),
        )

    async def _wait_until_ready(self, max_wait_sec: int = 60) -> None:
        """
        Ollama가 health(모델 목록 응답) 가능해질 때까지 대기.
        api/tags가 200이면 OK.
        """
        url = f"{self.base}/api/tags"
        deadline = asyncio.get_event_loop().time() + max_wait_sec
        async with httpx.AsyncClient(timeout=httpx.Timeout(5)) as cx:
            while True:
                try:
                    r = await cx.get(url)
                    if r.status_code == 200:
                        return
                except Exception:
                    pass
                if asyncio.get_event_loop().time() >= deadline:
                    return  # 대기 실패해도 generate에서 재시도로 커버
                await asyncio.sleep(1.0)

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 800,
        temperature: float = 0.0,
        *,
        num_ctx: Optional[int] = None,
        num_predict: Optional[int] = None,
    ) -> str:
        # 준비 상태 대기(일시적인 헬스체크 레이스 방지)
        await self._wait_until_ready()

        # CPU 환경에서 지나치게 긴 생성은 느리므로 기본값을 보수적으로 clamp
        final_num_ctx = int(num_ctx or self.num_ctx)
        # max_tokens 요청이 오더라도 기본 상한(ENV)으로 최소화해 속도 확보
        final_num_predict = int(num_predict or min(max_tokens, self.num_predict_default))

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "temperature": float(temperature),
                "top_p": 1.0,
                "num_ctx": final_num_ctx,
                "num_predict": final_num_predict,
                # CPU에서 안정/일관성 및 속도 측면에서 무난한 기본치
                "top_k": 20,
                "mirostat": 0,
                # 스레드 힌트(환경 따라 무시될 수 있음). 필요시 ENV로 빼도 됨.
                "num_thread": _int_from_env("OLLAMA_NUM_THREAD", 4),
            },
            "stream": False,
        }

        # 지수 백오프 재시도 (연결/타임아웃/일시적 5xx 방어)
        last_err: Optional[Exception] = None
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as cx:
                    r = await cx.post(f"{self.base}/api/generate", json=payload)
                    r.raise_for_status()
                    return r.json().get("response", "").strip()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout, httpx.HTTPStatusError) as e:
                last_err = e
                # 바로 재시도 하지 말고 지수 백오프
                sleep_s = min(0.5 * (2 ** (attempt - 1)), 8.0)
                await asyncio.sleep(sleep_s)
            except Exception as e:
                last_err = e
                await asyncio.sleep(1.0)

        # 모든 시도 실패 시 마지막 예외 throw
        raise last_err if last_err else RuntimeError("Unknown error in LLMClient.generate")

    # --------------------- 저장 유틸 ---------------------
    @staticmethod
    def _ensure_dir(p: str | Path) -> Path:
        p = Path(p)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def save_real_outputs(
        data: Any,
        out_dir: str | Path = "real_outputs",
        filename: Optional[str] = None,
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> Path:
        """
        data(dict/list/str)를 real_outputs/ 아래 안전 저장.
        - filename 미지정 시: results_YYYYmmdd_HHMMSS.json|.txt 자동 결정
        - dict/list -> .json, str -> .txt
        """
        out_root = LLMClient._ensure_dir(out_dir)

        if isinstance(data, (dict, list)):
            if not filename:
                filename = f"results_{_ts()}.json"
            path = out_root / filename
            if not path.suffix:
                path = path.with_suffix(".json")
            path.write_text(json.dumps(data, ensure_ascii=ensure_ascii, indent=indent), encoding="utf-8")
            return path

        # 문자열인 경우
        if not filename:
            filename = f"results_{_ts()}.txt"
        path = out_root / filename
        if not path.suffix:
            path = path.with_suffix(".txt")
        path.write_text(str(data), encoding="utf-8")
        return path