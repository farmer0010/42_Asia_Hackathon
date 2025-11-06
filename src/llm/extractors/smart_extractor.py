import requests
import json
from typing import Dict, Any, List
import re

class SmartExtractor:
    def __init__(self, ollama_url="http://localhost:11434"):
        """LLM 기반 스마트 추출기"""
        self.ollama_url = ollama_url
        self.model = "qwen2.5:7b"
        
        self.schemas = {
            "invoice": {
                "fields": [
                    "invoice_number",
                    "invoice_date",
                    "vendor_name",
                    "total_amount",
                    "currency"
                ],
                "description": "청구서/세금계산서"
            },
            "receipt": {
                "fields": [
                    "merchant_name",
                    "purchase_date",
                    "total_amount",
                    "payment_method"
                ],
                "description": "영수증"
            },
            "resume": {
                "fields": [
                    "candidate_name",
                    "email",
                    "phone",
                    "education",
                    "work_experience"
                ],
                "description": "이력서"
            },
            "report": {
                "fields": [
                    "title",
                    "author",
                    "date"
                ],
                "description": "보고서"
            },
            "contract": {
                "fields": [
                    "contract_title",
                    "parties",
                    "effective_date"
                ],
                "description": "계약서"
            }
        }
    def extract(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        메인 추출 함수
        Args:
            prediction: predictions_ocr_only.json의 각 항목
        Returns:
            extracted_data 딕셔너리
        """
        doc_type = prediction.get('classification', {}).get('doc_type', 'unknown')
        
        # unknown이거나 추출 불필요한 타입은 빈 딕셔너리 반환
        if doc_type == 'unknown' or doc_type not in self.schemas:
            return {}
        
        # 프롬프트 생성
        prompt = self._build_prompt(prediction)
        
        # Ollama API 호출
        response = self._call_ollama(prompt)
        
        # JSON 파싱
        extracted = self._parse_json_response(response)
        
        return extracted
    
    def _build_prompt(self, prediction: Dict[str, Any]) -> str:
        """프롬프트 생성 (다국어 지원)"""
        doc_type = prediction.get('classification', {}).get('doc_type', 'unknown')
        full_text = prediction.get('full_text_ocr', '')
        layout = prediction.get('layout', {})
        sections = layout.get('sections', [])
        detected_lang = prediction.get('detected_language', 'en')
        
        # 스키마 가져오기
        schema = self.schemas.get(doc_type, {})
        fields = schema.get('fields', [])
        description = schema.get('description', doc_type)
        
        # sections에서 key-value 쌍 추출 (최대 10개)
        key_values = []
        for section in sections[:10]:  # 상위 10개만
            if section.get('type') == 'key_value':
                text = section.get('text', '')
                if text:
                    key_values.append(text)
        
        # 언어별 힌트
        lang_hints = {
            'en': 'English',
            'thai': 'Thai (ภาษาไทย)',
            'korean': 'Korean (한국어)',
            'japan': 'Japanese (日本語)'
        }
        detected_lang_name = lang_hints.get(detected_lang, 'Unknown')
        
        # 프롬프트 구성 (다국어 대응)
        prompt = f"""You are a multilingual document data extraction expert.
You can process documents in English, Thai, Korean, Japanese, and other languages.

Document Type: {description} ({doc_type})
Detected Language: {detected_lang_name}

Full OCR Text (first 800 chars - may contain {detected_lang_name} text):
{full_text[:800]}

Key Information Found:
{chr(10).join(f"- {kv}" for kv in key_values) if key_values else "- No key-value pairs detected"}

Extract the following fields as a JSON object:
{json.dumps(fields, indent=2)}

Rules:
1. Output ONLY valid JSON, no explanation
2. Use null for missing fields
3. Keep original format (dates, numbers) and preserve original language in values
4. Field names should be in English, but values can be in the document's original language ({detected_lang_name})
5. If text contains mixed languages, extract the primary language value
6. For non-ASCII text (Thai, Korean, Japanese), preserve the original characters
7. Be concise and accurate

JSON Output:"""
        
        return prompt

    def _call_ollama(self, prompt: str) -> str:
        """Ollama API 호출"""
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1,  # 낮을수록 일관성 높음
            "options": {
                "num_predict": 500  # 최대 토큰 수
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=180)  # CPU 모드 고려
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except requests.exceptions.ConnectionError:
            print(f"Error: Cannot connect to Ollama at {self.ollama_url}")
            return ""
        except requests.exceptions.Timeout:
            print(f"Error: Ollama request timeout")
            return ""
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return ""
    
    def _parse_json_response(self, response: str) -> Dict:
        """JSON 응답 파싱"""
        if not response:
            return {}
        
        # 패턴 1: ```json ... ``` 형식
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 패턴 2: { ... } 형식
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # 그냥 전체 시도
                json_str = response.strip()
        
        # JSON 파싱 시도
        try:
            data = json.loads(json_str)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON: {e}")
            print(f"Response was: {response[:200]}...")
            return {}