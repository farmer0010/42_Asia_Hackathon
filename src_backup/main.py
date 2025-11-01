from ocr_module import OCRModule
from classification_module import DocumentClassifier
from pathlib import Path
import json
import argparse
from extraction_module import DataExtractor


def process_document(image_path, ocr, classifier, extractor):
    """
    단일 문서 처리: OCR -> 분류 -> 결과
    """
    print(f"\nProcessing: {Path(image_path).name}")
    print("-" * 60)
    
    #  OCR
    print("Step 1: OCR extraction...")
    ocr_result = ocr.extract_text(image_path)
    
    if 'error' in ocr_result:
        print(f"OCR Error: {ocr_result['error']}")
        return None
    
    print(f"  Extracted {len(ocr_result['text'])} characters")
    print(f"  Confidence: {ocr_result['confidence']:.2%}")
    
    #  분류
    print("\nStep 2: Document classification...")
    classification = classifier.classify(ocr_result['text'])
    print(f"  Type: {classification['doc_type']}")
    print(f"  Confidence: {classification['confidence']:.2%}")
    
    extracted_data = {}
    if extractor:
        print("\nStep 3: Structured extraction...")
        extracted_data = extractor.extract(
            ocr_result['text'],
            classification['doc_type']
        )
        if extracted_data:
            print(f"  Extracted {len(extracted_data)} fields")
        else:
            print("  No extraction for this doc type")
    
    # 결과 조합
    result = {
        'filename': Path(image_path).name,
        'full_text_ocr': ocr_result['text'],
        'ocr_confidence': ocr_result['confidence'],
        'classification': classification,
        'extracted_data': extracted_data,
        'processing_time': ocr_result['processing_time']
    }
    
    return result



def main():
    print("=" * 60)
    print("Document Processing Pipeline")
    print("=" * 60)
    
    # 1. 명령줄 인자
    parser = argparse.ArgumentParser(description='Process document with OCR and classification')
    parser.add_argument('--input', required=True, help='Input image/PDF file')
    parser.add_argument('--classifier', required=True, help='Path to trained classifier model')
    parser.add_argument('--output', help='Output JSON file (optional)')
    args = parser.parse_args()
    
    # 2. 파일 확인
    if not Path(args.input).exists():
        print(f"Error: {args.input} not found!")
        return
    
    if not Path(args.classifier).exists():
        print(f"Error: {args.classifier} not found!")
        return
    
    # 3. 모듈 초기화
    print("\nInitializing modules...")
    ocr = OCRModule()
    classifier = DocumentClassifier()
    classifier.load_model(args.classifier)
    print("Modules ready!")
    
    extractor = None
    # 추출 기능은 나중에 labels.csv와 함께 설정
    # extractor = DataExtractor()
    # extractor.configure_from_labels('labels.csv')

    # 4. 문서 처리
    result = process_document(args.input, ocr, classifier, extractor)
    
    if result is None:
        print("\nProcessing failed!")
        return
    
    # 5. 결과 출력
    print("\n")
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 6. 파일 저장 (선택)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {args.output}")