import sys
sys.path.append('srcs')

from ocr_vl_module import OCRVLModule
from pathlib import Path
import json
import argparse
from tqdm import tqdm

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
    """
    # Step 1: OCR-VL
    ocr_result = ocr_vl.process_document(str(image_path))
    
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
    
    # Step 3: 최종 JSON (LLM 팀에게 전달)
    result = {
        "filename": Path(image_path).name,
        "full_text_ocr": ocr_result['full_text'],
        "ocr_confidence": ocr_result['confidence'],
        "layout": ocr_result['layout'],
        "classification": classification,
        "processing_time": ocr_result['processing_time']
    }
    
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
        sys.path.append('src_backup')  # classification_module 위치
        from classification_module import DocumentClassifier
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