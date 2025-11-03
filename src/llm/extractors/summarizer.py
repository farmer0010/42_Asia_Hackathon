from typing import Dict
from .smart_extractor import SmartExtractor

class DocumentSummarizer(SmartExtractor):
    """
    문서 요약 생성기
    - Report: 핵심 내용, 결론 요약
    - Contract: 주요 조항, 당사자, 기간 요약
    """
    
    def __init__(self, ollama_url="http://localhost:11434"):
        super().__init__(ollama_url)
    
    def summarize(self, text: str, doc_type: str) -> str:
        """
        문서 요약 생성
        
        Args:
            text: 문서 전체 텍스트
            doc_type: 문서 타입 (report or contract)
        
        Returns:
            요약 텍스트
        """
        if doc_type not in ['report', 'contract']:
            return ""
        
        # 텍스트가 너무 길면 앞부분만 (LLM context 제한)
        text_snippet = text[:2000]
        
        if doc_type == 'report':
            return self._summarize_report(text_snippet)
        elif doc_type == 'contract':
            return self._summarize_contract(text_snippet)
        
        return ""
    
    def _summarize_report(self, text: str) -> str:
        """보고서 요약"""
        prompt = f"""Summarize this report document in 3-5 sentences.

Document text:
{text}

Focus on:
- Main topic or purpose
- Key findings or results
- Important conclusions

Summary (3-5 sentences, concise):"""
        
        try:
            response = self._call_ollama(prompt)
            # 응답에서 요약 추출
            summary = response.strip()
            
            # 너무 길면 자르기 (500자 제한)
            if len(summary) > 500:
                summary = summary[:497] + "..."
            
            return summary
            
        except Exception as e:
            print(f"Warning: Report summarization failed: {e}")
            return "Summary generation failed."
    
    def _summarize_contract(self, text: str) -> str:
        """계약서 요약"""
        prompt = f"""Summarize this contract document in 3-5 sentences.

Document text:
{text}

Focus on:
- Parties involved
- Main subject/purpose of contract
- Key terms or conditions
- Duration or dates (if mentioned)

Summary (3-5 sentences, concise):"""
        
        try:
            response = self._call_ollama(prompt)
            summary = response.strip()
            
            # 너무 길면 자르기 (500자 제한)
            if len(summary) > 500:
                summary = summary[:497] + "..."
            
            return summary
            
        except Exception as e:
            print(f"Warning: Contract summarization failed: {e}")
            return "Summary generation failed."