import httpx

class LLMClient:
    def __init__(self, model="gemma3:4b", base="http://localhost:11434"):
        self.base = base
        self.model = model

    async def generate(self, prompt, max_tokens=800, temperature=0.0):
        async with httpx.AsyncClient(timeout=40) as cx:
            payload = {
                "model": self.model,
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