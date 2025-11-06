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
        
        # 정규식 패턴 정의 (다국어 지원)
        self.patterns = {
            # 공통
            "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "CREDIT_CARD": r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}',
            
            # 전화번호 - 영어권
            "PHONE_NUMBER": r'[\+]?[0-9]{1,3}?[-.\s]?\(?[0-9]{1,4}\)?[-.\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}',
            
            # 태국
            "THAI_ID": r'\d{1}-\d{4}-\d{5}-\d{2}-\d{1}',
            "THAI_PHONE": r'0[0-9]{1}-[0-9]{3,4}-[0-9]{4}',  # 예: 02-123-4567
            
            # 한국
            "KOREAN_PHONE": r'0[0-9]{1,2}-[0-9]{3,4}-[0-9]{4}',  # 예: 010-1234-5678
            "KOREAN_ID": r'\d{6}-[1-4]\d{6}',  # 주민번호 (마스킹 필수!)
            
            # 일본
            "JAPAN_PHONE": r'0[0-9]{1,4}-[0-9]{1,4}-[0-9]{4}',  # 예: 03-1234-5678
            "JAPAN_MY_NUMBER": r'\d{4}[-\s]?\d{4}[-\s]?\d{4}',  # 마이넘버
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
    
    def mask_text(self, text: str, pii_type: str) -> str:
        """
        단일 PII 텍스트 마스킹
        
        Args:
            text: 원본 PII 텍스트
            pii_type: PII 타입
        
        Returns:
            마스킹된 텍스트
        """
        if not text:
            return "***"
        
        if pii_type == "EMAIL":
            # john.doe@company.com -> j***@c***.com
            if '@' in text:
                parts = text.split('@')
                name = parts[0]
                domain_parts = parts[1].split('.')
                
                if len(name) > 0 and len(domain_parts) >= 2:
                    masked_name = name[0] + '***' if len(name) > 1 else name
                    masked_domain = domain_parts[0][0] + '***' if len(domain_parts[0]) > 1 else domain_parts[0]
                    ext = '.'.join(domain_parts[1:])
                    return f"{masked_name}@{masked_domain}.{ext}"
            return "***@***.***"
        
        elif pii_type == "PHONE_NUMBER":
            # +1-555-1234 -> +1-5**-**34
            digits = re.sub(r'\D', '', text)
            if len(digits) >= 6:
                masked_digits = digits[:2] + '*' * (len(digits) - 4) + digits[-2:]
                # 원본 형식 유지하면서 숫자만 마스킹
                result = text
                for i, d in enumerate(digits):
                    if i >= 2 and i < len(digits) - 2:
                        result = result.replace(d, '*', 1)
                return result
            return "***"
        
        elif pii_type == "PERSON_NAME":
            # John Doe -> J*** D***
            words = text.split()
            if len(words) >= 2:
                masked = [word[0] + '***' for word in words]
                return ' '.join(masked)
            elif len(words) == 1:
                return text[0] + '***' if len(text) > 1 else text
            return "***"
        
        elif pii_type == "ADDRESS":
            # 1234 Main Street, City -> 123*** (주소 일부만)
            if len(text) > 10:
                return text[:3] + '***'
            return "***"
        
        elif pii_type == "THAI_ID":
            # 1-1020-30405-60-7 -> 1-****-*****-**-*
            parts = text.split('-')
            if len(parts) == 5:
                return f"{parts[0]}-****-*****-**-*"
            return "***"
        
        elif pii_type == "CREDIT_CARD":
            # 1234 5678 9012 3456 -> **** **** **** 3456
            digits = re.sub(r'\D', '', text)
            if len(digits) >= 4:
                return '**** **** **** ' + digits[-4:]
            return "****"
        
        elif pii_type == "THAI_PHONE":
            # 02-123-4567 -> 02-***-**67
            parts = text.split('-')
            if len(parts) == 3:
                return f"{parts[0]}-***-**{parts[2][-2:]}"
            return "***"
        
        elif pii_type == "KOREAN_PHONE":
            # 010-1234-5678 -> 010-****-**78
            parts = text.split('-')
            if len(parts) == 3:
                return f"{parts[0]}-****-**{parts[2][-2:]}"
            return "***"
        
        elif pii_type == "KOREAN_ID":
            # 123456-1234567 -> 123456-*******  (주민번호 완전 마스킹)
            parts = text.split('-')
            if len(parts) == 2:
                return f"{parts[0]}-*******"
            return "***"
        
        elif pii_type == "JAPAN_PHONE":
            # 03-1234-5678 -> 03-****-**78
            parts = text.split('-')
            if len(parts) == 3:
                return f"{parts[0]}-****-**{parts[2][-2:]}"
            return "***"
        
        elif pii_type == "JAPAN_MY_NUMBER":
            # 1234-5678-9012 -> ****-****-**12
            parts = text.split('-')
            if len(parts) == 3:
                return f"****-****-**{parts[2][-2:]}"
            return "****"
        
        # 기본: 앞 1-2자만 보이고 나머지 마스킹
        if len(text) > 3:
            return text[:2] + '***'
        return '***'
    
    def mask_full_text(self, text: str, pii_list: List[Dict]) -> str:
        """
        전체 텍스트에서 모든 PII 마스킹
        
        Args:
            text: 원본 전체 텍스트
            pii_list: 탐지된 PII 리스트
        
        Returns:
            마스킹된 전체 텍스트
        """
        if not text or not pii_list:
            return text
        
        masked_text = text
        
        # 긴 것부터 처리 (겹치는 것 방지)
        sorted_pii = sorted(pii_list, key=lambda x: len(x['text']), reverse=True)
        
        for pii in sorted_pii:
            original = pii['text']
            masked = pii.get('masked', self.mask_text(original, pii['type']))
            
            # 대소문자 구분 없이 교체
            masked_text = re.sub(re.escape(original), masked, masked_text, flags=re.IGNORECASE)
        
        return masked_text

