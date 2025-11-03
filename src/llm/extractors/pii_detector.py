import re
from typing import List, Dict
from .smart_extractor import SmartExtractor

class PIIDetector(SmartExtractor):
    """
    개인 식별 정보(PII) 탐지기
    - 정규식: 빠른 패턴 매칭 (이메일, 전화, ID)
    - LLM: 복잡한 패턴 (이름, 주소)
    """
    
    def __init__(self, ollama_url="http://localhost:11434"):
        super().__init__(ollama_url)
        
        # 정규식 패턴 정의
        self.patterns = {
            "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "PHONE_NUMBER": r'[\+]?[0-9]{1,3}?[-.\s]?\(?[0-9]{1,4}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}',
            "THAI_ID": r'\d{1}-\d{4}-\d{5}-\d{2}-\d{1}',
            "CREDIT_CARD": r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
        }
    
    def detect(self, text: str, use_llm: bool = True) -> List[Dict]:
        """
        PII 탐지
        
        Args:
            text: 탐지할 텍스트
            use_llm: LLM 사용 여부 (False면 정규식만)
        
        Returns:
            [{"type": "EMAIL", "text": "john@example.com"}, ...]
        """
        pii_list = []
        
        # 1. 정규식으로 빠른 탐지
        pii_list.extend(self._detect_with_regex(text))
        
        # 2. LLM으로 복잡한 것 탐지 (선택적)
        if use_llm and text.strip():
            pii_list.extend(self._detect_with_llm(text))
        
        # 중복 제거
        return self._deduplicate(pii_list)
    
    def _detect_with_regex(self, text: str) -> List[Dict]:
        """정규식 기반 PII 탐지"""
        found = []
        
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            for match in matches:
                found.append({
                    "type": pii_type,
                    "text": match.strip()
                })
        
        return found
    
    def _detect_with_llm(self, text: str) -> List[Dict]:
        """LLM 기반 PII 탐지 (이름, 주소)"""
        # 텍스트가 너무 길면 앞부분만
        text_snippet = text[:800]
        
        prompt = f"""Find personal identifiable information (PII) in this text.

Text:
{text_snippet}

Extract only:
- PERSON_NAME: people's full names
- ADDRESS: complete addresses

Output JSON only, no explanation:
{{"names": [], "addresses": []}}"""
        
        try:
            # 부모 클래스의 메서드 재사용!
            response = self._call_ollama(prompt)
            data = self._parse_json_response(response)
            
            found = []
            
            # 이름 추가
            for name in data.get('names', []):
                if name and len(name) > 1:  # 너무 짧으면 제외
                    found.append({
                        "type": "PERSON_NAME",
                        "text": name
                    })
            
            # 주소 추가
            for addr in data.get('addresses', []):
                if addr and len(addr) > 5:  # 너무 짧으면 제외
                    found.append({
                        "type": "ADDRESS",
                        "text": addr
                    })
            
            return found
            
        except Exception as e:
            print(f"Warning: LLM PII detection failed: {e}")
            return []
    
    def _deduplicate(self, pii_list: List[Dict]) -> List[Dict]:
        """중복 제거"""
        seen = set()
        unique = []
        
        for item in pii_list:
            key = (item['type'], item['text'].lower())
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique

