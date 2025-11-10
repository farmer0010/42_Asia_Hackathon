from typing import Optional
from .smart_extractor import SmartExtractor

class DocumentSummarizer(SmartExtractor):
    """
    report/contract 고급 요약. model/retries를 상속 초기화에서 그대로 사용.
    """

    def __init__(self, ollama_url: str = "http://localhost:11434", model: Optional[str] = None, retries: int = 0):
        super().__init__(ollama_url=ollama_url, model=model, retries=retries)

    def summarize(self, text: str, doc_type: str) -> str:
        if doc_type not in ("report", "contract"):
            return ""
        snippet = text[:2000]
        if doc_type == "report":
            prompt = (
                "Summarize this report in 3-5 concise sentences. Plain text only.\n"
                "Focus on: main topic, key findings/results, important conclusions.\n\n"
                f"Text:\n{snippet}\n"
            )
        else:
            prompt = (
                "Summarize this contract in 3-5 concise sentences. Plain text only.\n"
                "Focus on: parties, purpose, key terms/conditions, duration/dates.\n\n"
                f"Text:\n{snippet}\n"
            )
        try:
            return (self._call_ollama(prompt) or "").strip()[:600]
        except Exception:
            return ""