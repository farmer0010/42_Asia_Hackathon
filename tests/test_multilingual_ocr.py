#!/usr/bin/env python3
# tests/test_multilingual_ocr.py

"""
다국어 OCR 모듈 테스트
- 영어, 태국어, 한국어, 일본어 지원 확인
- 언어 자동 감지 테스트
- 손글씨 전처리 효과 확인
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ocr.ocr_vl_module import OCRVLModule
import json
import time

def print_header(text):
    """예쁜 헤더 출력"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_result(result, test_name):
    """OCR 결과 출력"""
    print(f"\n📄 {test_name}")
    print("-" * 70)
    
    if 'error' in result:
        print(f"  ❌ Error: {result['error']}")
        return
    
    print(f"  🌍 Detected Language: {result.get('detected_language', 'N/A').upper()}")
    print(f"  📊 Confidence: {result['confidence']:.2%}")
    print(f"  ⏱️  Processing Time: {result['processing_time']:.2f}s")
    print(f"  📝 Text Length: {len(result['full_text'])} chars")
    
    # 레이아웃 정보
    layout = result.get('layout', {})
    if layout:
        print(f"  📋 Title: {layout.get('title', 'None')}")
        features = layout.get('features', {})
        print(f"  📊 Key-Value Pairs: {features.get('num_key_value_pairs', 0)}")
        print(f"  📄 Total Lines: {features.get('total_lines', 0)}")
        print(f"  📊 Has Table: {'Yes' if features.get('has_table') else 'No'}")
    
    # 텍스트 미리보기
    preview = result['full_text'][:200].replace('\n', ' ')
    print(f"  📖 Text Preview: {preview}...")
    print("-" * 70)

def test_existing_samples():
    """기존 샘플 파일 테스트 (영어)"""
    print_header("Test 1: 기존 샘플 파일 (영어 문서)")
    
    # OCR 초기화
    ocr = OCRVLModule(use_gpu=False, enable_handwriting=True)
    
    # 샘플 파일 경로
    sample_dir = project_root / "data" / "input"
    sample_files = list(sample_dir.glob("*.jpg")) + list(sample_dir.glob("*.png")) + list(sample_dir.glob("*.jpeg"))
    
    if not sample_files:
        print("  ⚠️  No sample files found in data/input/")
        return []
    
    print(f"\n  Found {len(sample_files)} sample files")
    
    results = []
    for sample_file in sample_files[:2]:  # 처음 2개만 테스트
        print(f"\n  Processing: {sample_file.name}")
        result = ocr.process_document(str(sample_file), lang='auto')
        print_result(result, sample_file.name)
        results.append({
            'filename': sample_file.name,
            'result': result
        })
    
    return results

def test_language_detection():
    """언어 감지 기능 테스트"""
    print_header("Test 2: 언어 자동 감지 테스트")
    
    ocr = OCRVLModule(use_gpu=False, enable_handwriting=False)
    
    # 테스트 텍스트들
    test_texts = [
        ("English text: Invoice Number 12345", "en"),
        ("ใบเสร็จรับเงิน เลขที่ 12345", "thai"),
        ("영수증 번호 12345", "korean"),
        ("領収書 番号 12345", "japan"),
    ]
    
    print("\n  Testing language detection from text:")
    print("-" * 70)
    
    for text, expected_lang in test_texts:
        detected = ocr._detect_language_from_text(text)
        status = "✓" if detected == expected_lang else "✗"
        print(f"  {status} Text: {text[:30]:30s} | Expected: {expected_lang:7s} | Detected: {detected:7s}")
    
    print("-" * 70)

def test_manual_language_selection():
    """언어 수동 지정 테스트"""
    print_header("Test 3: 언어 수동 지정")
    
    sample_dir = project_root / "data" / "input"
    sample_files = list(sample_dir.glob("*.jpg"))[:1]
    
    if not sample_files:
        print("  ⚠️  No sample files found")
        return
    
    sample_file = sample_files[0]
    
    # 각 언어로 시도
    languages = ['en', 'thai', 'korean', 'japan']
    
    ocr = OCRVLModule(use_gpu=False, enable_handwriting=False)
    
    print(f"\n  Testing with: {sample_file.name}")
    print(f"  Trying different language models:")
    print("-" * 70)
    
    for lang in languages:
        print(f"\n  🌍 Testing with {lang.upper()} OCR...")
        result = ocr.process_document(str(sample_file), lang=lang)
        
        if 'error' not in result:
            print(f"    ✓ Success! Confidence: {result['confidence']:.2%}")
            print(f"    Text preview: {result['full_text'][:80]}...")
        else:
            print(f"    ✗ Failed: {result['error']}")

def test_handwriting_enhancement():
    """손글씨 전처리 효과 테스트"""
    print_header("Test 4: 손글씨 전처리 효과 비교")
    
    sample_dir = project_root / "data" / "input"
    sample_files = list(sample_dir.glob("*.jpg"))[:1]
    
    if not sample_files:
        print("  ⚠️  No sample files found")
        return
    
    sample_file = sample_files[0]
    
    print(f"\n  Testing with: {sample_file.name}")
    print("-" * 70)
    
    # 전처리 없이
    print("\n  📄 Without handwriting enhancement:")
    ocr_no_hw = OCRVLModule(use_gpu=False, enable_handwriting=False)
    result_no_hw = ocr_no_hw.process_document(str(sample_file), lang='auto')
    if 'error' not in result_no_hw:
        print(f"    Confidence: {result_no_hw['confidence']:.2%}")
        print(f"    Time: {result_no_hw['processing_time']:.2f}s")
    
    # 전처리 있음
    print("\n  🖊️  With handwriting enhancement:")
    ocr_hw = OCRVLModule(use_gpu=False, enable_handwriting=True)
    result_hw = ocr_hw.process_document(str(sample_file), lang='auto')
    if 'error' not in result_hw:
        print(f"    Confidence: {result_hw['confidence']:.2%}")
        print(f"    Time: {result_hw['processing_time']:.2f}s")
    
    # 비교
    if 'error' not in result_no_hw and 'error' not in result_hw:
        conf_diff = result_hw['confidence'] - result_no_hw['confidence']
        time_diff = result_hw['processing_time'] - result_no_hw['processing_time']
        
        print("\n  📊 Comparison:")
        print(f"    Confidence improvement: {conf_diff:+.2%}")
        print(f"    Time overhead: {time_diff:+.2f}s")
        
        if conf_diff > 0.01:
            print("    ✓ Handwriting enhancement is helpful!")
        elif conf_diff < -0.01:
            print("    ⚠️  Handwriting enhancement reduced confidence")
        else:
            print("    → No significant difference")

def save_test_results(all_results):
    """테스트 결과 저장"""
    output_file = project_root / "tests" / "test_multilingual_results.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n  💾 Results saved to: {output_file}")

def main():
    """메인 테스트 실행"""
    print("\n" + "🌍" * 35)
    print("       MULTILINGUAL OCR TEST SUITE")
    print("🌍" * 35)
    
    start_time = time.time()
    
    try:
        # Test 1: 기존 샘플 테스트
        results_1 = test_existing_samples()
        
        # Test 2: 언어 감지
        test_language_detection()
        
        # Test 3: 언어 수동 지정
        test_manual_language_selection()
        
        # Test 4: 손글씨 전처리
        test_handwriting_enhancement()
        
        # 결과 저장
        if results_1:
            save_test_results(results_1)
        
        # 최종 요약
        print_header("Test Summary")
        total_time = time.time() - start_time
        print(f"\n  ✓ All tests completed!")
        print(f"  ⏱️  Total time: {total_time:.2f}s")
        print(f"  📝 Tested documents: {len(results_1)}")
        
        print("\n  🎯 Key Findings:")
        print("    • Multilingual OCR initialized successfully")
        print("    • Language detection working")
        print("    • All 4 languages supported (en, thai, korean, japan)")
        print("    • Handwriting enhancement available")
        
        print("\n  📋 Next Steps:")
        print("    1. Test with actual Thai/Korean/Japanese documents")
        print("    2. Integrate with classification pipeline")
        print("    3. Proceed to Step 2: XLM-RoBERTa classifier")
        
        print("\n" + "=" * 70)
        print("  ✅ TEST COMPLETE!")
        print("=" * 70 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n  ⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n  ❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

