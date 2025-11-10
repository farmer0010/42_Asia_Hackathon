#!/usr/bin/env python3
"""
PII 마스킹 기능 테스트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.extractors.pii_detector import PIIDetector

def test_pii_masking():
    """PII 마스킹 기능 테스트"""
    
    print("=" * 60)
    print("PII Masking Test")
    print("=" * 60)
    print()
    
    # PIIDetector 초기화 (LLM 없이 테스트)
    detector = PIIDetector(ollama_url="http://localhost:11434")
    
    # 테스트 케이스
    test_cases = [
        ("EMAIL", "john.doe@company.com"),
        ("EMAIL", "alice@example.org"),
        ("PHONE_NUMBER", "+1-555-1234"),
        ("PHONE_NUMBER", "010-1234-5678"),
        ("PERSON_NAME", "John Doe"),
        ("PERSON_NAME", "Kim Min-su"),
        ("ADDRESS", "1234 Main Street, New York, NY"),
        ("THAI_ID", "1-1020-30405-60-7"),
        ("CREDIT_CARD", "1234 5678 9012 3456"),
    ]
    
    print("Individual PII Masking:")
    print("-" * 60)
    
    for pii_type, original in test_cases:
        masked = detector.mask_text(original, pii_type)
        print(f"{pii_type:15} | {original:30} → {masked}")
    
    print()
    print("=" * 60)
    print("Full Text Masking:")
    print("-" * 60)
    print()
    
    # 전체 텍스트 테스트
    full_text = """
    Invoice from john.doe@company.com
    Phone: +1-555-1234
    Customer: Alice Smith
    Address: 1234 Main Street, New York
    Thai ID: 1-1020-30405-60-7
    Card: 1234 5678 9012 3456
    """
    
    # PII 탐지 (정규식만, LLM 없이)
    pii_list = detector._detect_with_regex(full_text)
    
    # 마스킹 추가
    for pii in pii_list:
        pii["masked"] = detector.mask_text(pii["text"], pii["type"])
    
    print("Detected PII:")
    for pii in pii_list:
        print(f"  {pii['type']:15} | {pii['text']:30} → {pii['masked']}")
    
    print()
    print("Original Text:")
    print(full_text)
    
    # 전체 텍스트 마스킹
    masked_text = detector.mask_full_text(full_text, pii_list)
    
    print("Masked Text:")
    print(masked_text)
    
    print()
    print("=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_pii_masking()

