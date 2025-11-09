#!/usr/bin/env python3
"""
PDF 멀티페이지 처리 테스트 스크립트
"""

from src.ocr.ocr_vl_module import OCRVLModule
import sys
import os

def test_pdf_processing(pdf_path):
    """PDF 멀티페이지 처리 테스트"""
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        print("\n💡 Usage:")
        print("  python test_pdf_multipage.py <pdf_file>")
        print("\nExample:")
        print("  python test_pdf_multipage.py data/input/contract.pdf")
        return
    
    print("=" * 70)
    print("📄 PDF Multipage Processing Test")
    print("=" * 70)
    print(f"\nFile: {pdf_path}\n")
    
    # OCR 초기화
    print("Initializing OCR module...")
    ocr = OCRVLModule(use_gpu=False, enable_handwriting=True)
    print("✓ OCR module ready!\n")
    
    # PDF 처리
    print("-" * 70)
    result = ocr.process_pdf_multipage(pdf_path, lang='auto', max_pages=3)
    print("-" * 70)
    
    # 결과 출력
    if 'error' in result:
        print("\n❌ Processing Failed!")
        print(f"Error: {result['error']}")
        return
    
    print("\n" + "=" * 70)
    print("📊 Results Summary")
    print("=" * 70)
    
    print(f"\n📄 PDF Information:")
    print(f"  Total pages: {result.get('total_pages', 'N/A')}")
    print(f"  Processed pages: {result.get('processed_pages', 'N/A')}")
    
    if result.get('total_pages', 0) > result.get('processed_pages', 0):
        skipped = result['total_pages'] - result['processed_pages']
        print(f"  Skipped pages: {skipped} (strategy: first 3 pages)")
    
    print(f"\n🔍 OCR Quality:")
    print(f"  Language detected: {result.get('detected_language', 'N/A').upper()}")
    print(f"  Average confidence: {result['confidence']:.2%}")
    print(f"  Processing time: {result['processing_time']:.2f}s")
    
    # 텍스트 통계
    text = result['full_text']
    lines = text.split('\n')
    chars = len(text)
    words = len(text.split())
    
    print(f"\n📝 Text Statistics:")
    print(f"  Total characters: {chars:,}")
    print(f"  Total words: {words:,}")
    print(f"  Total lines: {len(lines):,}")
    
    # 페이지별 구분 확인
    page_markers = [line for line in lines if line.startswith('[Page ')]
    print(f"  Page markers found: {len(page_markers)}")
    for marker in page_markers:
        print(f"    - {marker}")
    
    # 텍스트 미리보기
    print(f"\n📖 Text Preview (first 800 characters):")
    print("-" * 70)
    print(text[:800])
    if len(text) > 800:
        print("\n... (truncated)")
    print("-" * 70)
    
    # 레이아웃 정보
    if result.get('layout'):
        layout = result['layout']
        print(f"\n📐 Layout Information (First Page):")
        print(f"  Title: {layout.get('title', 'N/A')}")
        print(f"  Has table: {layout.get('features', {}).get('has_table', False)}")
        print(f"  Key-value pairs: {layout.get('features', {}).get('num_key_value_pairs', 0)}")
        print(f"  Text density: {layout.get('features', {}).get('text_density', 0):.2f}")
    
    print("\n" + "=" * 70)
    print("✅ Test Complete!")
    print("=" * 70)
    
    # 전략 설명
    print("\n💡 PDF Processing Strategy:")
    print("  - If total pages ≤ 3: Process ALL pages")
    print("  - If total pages > 3: Process FIRST 3 pages only")
    print("  - Reason: Most important content is in first 3 pages")
    print("  - Memory efficient: Process one page at a time")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Error: PDF file path required")
        print("\n💡 Usage:")
        print("  python test_pdf_multipage.py <pdf_file>")
        print("\nExample:")
        print("  python test_pdf_multipage.py data/input/contract.pdf")
        print("\n📝 Note:")
        print("  - If you don't have a PDF, you can test with image files")
        print("  - The script will work with .jpg, .png files too")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    test_pdf_processing(pdf_path)

