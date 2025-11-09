from src.ocr.ocr_vl_module import OCRVLModule
from src.classification.classifier import DocumentClassifier
from pathlib import Path
import json
import argparse
from tqdm import tqdm
import sys

def prepare_classification_input(ocr_result):
    """
    OCR-VL 결과를 분류 입력으로 변환
    레이아웃 정보를 텍스트에 추가
    """
    text = ocr_result['full_text']
    layout = ocr_result['layout']
    
    layout_info = f"""
[LAYOUT_INFO]
Title: {layout.get('title', 'None')}
Has_Table: {layout['features']['has_table']}
Key_Value_Pairs: {layout['features']['num_key_value_pairs']}
Text_Density: {layout['features']['text_density']:.2f}
Total_Lines: {layout['features']['total_lines']}
[END_LAYOUT_INFO]
"""
    
    # 텍스트 앞부분만 + 레이아웃 정보
    return text[:2000] + "\n\n" + layout_info


def process_single_document(image_path, ocr_vl, classifier=None):
    """
    단일 문서 처리: OCR-VL + 분류(선택)
    
    다국어 지원:
    - OCR 자동 언어 감지
    - 감지된 언어 정보를 분류기 및 LLM에 전달
    
    PDF 지원:
    - PDF 파일 자동 감지
    - 멀티페이지 처리 (N≤3: 전체, N>3: 첫 3페이지)
    """
    # Step 1: PDF vs 이미지 구분
    file_path = Path(image_path)
    is_pdf = file_path.suffix.lower() == '.pdf'
    
    # Step 2: OCR 처리
    if is_pdf:
        # PDF 멀티페이지 처리
        ocr_result = ocr_vl.process_pdf_multipage(str(image_path), lang='auto')
    else:
        # 일반 이미지 처리
        ocr_result = ocr_vl.process_document(str(image_path), lang='auto')
    
    if 'error' in ocr_result:
        print(f"  ❌ OCR error: {ocr_result['error']}")
        return None
    
    # Step 2: 분류 (모델이 있으면)
    if classifier:
        enhanced_text = prepare_classification_input(ocr_result)
        classification = classifier.classify(enhanced_text)
    else:
        # 분류 모델 없으면 None
        classification = {
            "doc_type": "unknown",
            "confidence": 0.0
        }
    
    # Step 3: 최종 JSON (LLM에 전달)
    result = {
        "filename": Path(image_path).name,
        "full_text_ocr": ocr_result['full_text'],
        "ocr_confidence": ocr_result['confidence'],
        "layout": ocr_result['layout'],
        "classification": classification,
        "detected_language": ocr_result.get('detected_language', 'en'),
        "processing_time": ocr_result['processing_time']
    }
    
    # PDF 관련 정보 추가 (있으면)
    if 'total_pages' in ocr_result:
        result['total_pages'] = ocr_result['total_pages']
        result['processed_pages'] = ocr_result['processed_pages']
    
    return result


def main():
    parser = argparse.ArgumentParser(description='OCR-VL + Classification pipeline')
    parser.add_argument('--input', required=True, help='Input directory')
    parser.add_argument('--classifier', help='Path to trained classifier model (optional)')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('--gpu', action='store_true', help='Use GPU')
    args = parser.parse_args()
    
    # OCR-VL 초기화
    print("Initializing OCR-VL...")
    ocr_vl = OCRVLModule(use_gpu=args.gpu)
    
    # 분류 모델 초기화 (있으면)
    classifier = None
    if args.classifier:
        print(f"Loading classifier from {args.classifier}...")
        classifier = DocumentClassifier()
        classifier.load_model(args.classifier)
        print("Classifier loaded!")
    else:
        print("⚠️  No classifier specified. Will skip classification.")
    
    print("Modules ready!\n")
    
    # 파일 수집
    input_dir = Path(args.input)
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf']:
        files.extend(input_dir.glob(ext))
    
    print(f"Found {len(files)} files\n")
    
    if not files:
        print("No files found!")
        return
    
    # 배치 처리
    results = []
    errors = []
    
    for file_path in tqdm(files, desc="Processing"):
        try:
            result = process_single_document(file_path, ocr_vl, classifier)
            
            if result:
                results.append(result)
            else:
                errors.append(file_path.name)
        
        except Exception as e:
            print(f"\n❌ Error processing {file_path.name}: {e}")
            errors.append(file_path.name)
    
    # 결과 저장
    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 통계
    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Total files: {len(files)}")
    print(f"Successful: {len(results)}")
    print(f"Errors: {len(errors)}")
    
    if results:
        # OCR 통계
        avg_ocr_conf = sum(r['ocr_confidence'] for r in results) / len(results)
        avg_time = sum(r['processing_time'] for r in results) / len(results)
        print(f"\nAverage OCR confidence: {avg_ocr_conf:.2%}")
        print(f"Average processing time: {avg_time:.2f}s")
        
        # PDF 통계
        pdf_docs = [r for r in results if 'total_pages' in r]
        if pdf_docs:
            total_pdf_pages = sum(r['total_pages'] for r in pdf_docs)
            processed_pdf_pages = sum(r['processed_pages'] for r in pdf_docs)
            print(f"\nPDF Statistics:")
            print(f"  PDF files: {len(pdf_docs)}")
            print(f"  Total pages: {total_pdf_pages}")
            print(f"  Processed pages: {processed_pdf_pages}")
            if total_pdf_pages > processed_pdf_pages:
                skipped = total_pdf_pages - processed_pdf_pages
                print(f"  Skipped pages: {skipped} (strategy: first 3 pages only)")
        
        # 분류 통계 (분류 모델이 있으면)
        if classifier:
            from collections import Counter
            types = [r['classification']['doc_type'] for r in results]
            print(f"\nDocument types:")
            for dtype, count in Counter(types).items():
                print(f"  {dtype}: {count}")
            
            avg_class_conf = sum(r['classification']['confidence'] for r in results) / len(results)
            print(f"\nAverage classification confidence: {avg_class_conf:.2%}")
    
    print(f"\n✓ Results saved to: {output_path}")
    print("\n💡 Next step:")
    if classifier:
        print("  → 이 파일을 LLM 팀에게 전달하세요!")
    else:
        print("  → 나중에 --classifier 옵션으로 분류 모델을 추가하세요")
        print("  → 지금은 OCR 결과만 저장됨")
    print("="*60)


if __name__ == "__main__":
    main()