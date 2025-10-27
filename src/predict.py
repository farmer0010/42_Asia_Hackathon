from ocr_module import OCRModule
from classification_module import DocumentClassifier
from extraction_module import DataExtractor
from pathlib import Path
import json
import argparse
from tqdm import tqdm

def main():
    print("=" * 60)
    print("Batch Prediction for Testing Set")
    print("=" * 60)
    
    # 1. 명령줄 인자
    parser = argparse.ArgumentParser(description='Predict on testing set')
    parser.add_argument('--input', required=True, help='Input directory with documents')
    parser.add_argument('--classifier', required=True, help='Path to trained classifier')
    parser.add_argument('--labels', help='labels.csv for extraction config (optional)')
    parser.add_argument('--output', default='predictions.json', help='Output JSON file')
    args = parser.parse_args()
    
    # 2. 입력 확인
    input_path = Path(args.input)
    if not input_path.exists():
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
    
    # Extractor 설정
    extractor = None
    if args.labels:
        print(f"Configuring extractor from {args.labels}...")
        extractor = DataExtractor()
        extractor.configure_from_labels(args.labels)
    
    print("Modules ready!")

    # 4. 파일 스캔
    print("\nScanning files...")
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf']:
        files.extend(input_path.glob(ext))
        files.extend(input_path.rglob(ext))  # 하위 폴더도 검색
    
    # 중복 제거
    files = list(set(files))
    
    if not files:
        print(f"No documents found in {args.input}")
        return
    
    print(f"Found {len(files)} documents")

    # 5. 일괄 처리
    print("\nProcessing documents...")
    results = []
    errors = []
    
    for file in tqdm(files, desc="Progress"):
        try:
            # OCR
            ocr_result = ocr.extract_text(str(file))
            if 'error' in ocr_result:
                errors.append({'filename': file.name, 'error': ocr_result['error']})
                continue
            
            # 분류
            classification = classifier.classify(ocr_result['text'])
            
            # 추출
            extracted_data = {}
            if extractor:
                extracted_data = extractor.extract(
                    ocr_result['text'],
                    classification['doc_type']
                )
            
            # 결과 저장
            result = {
                'filename': file.name,
                'full_text_ocr': ocr_result['text'],
                'ocr_confidence': ocr_result['confidence'],
                'classification': classification,
                'extracted_data': extracted_data
            }
            results.append(result)
            
        except Exception as e:
            errors.append({'filename': file.name, 'error': str(e)})

    # 6. 결과 저장
    print(f"\nProcessed: {len(results)} documents")
    if errors:
        print(f"Errors: {len(errors)} documents")
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {args.output}")
    
    # 에러 로그
    if errors:
        error_file = args.output.replace('.json', '_errors.json')
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)
        print(f"Errors saved to: {error_file}")
    
    print("\n" + "=" * 60)
    print("Batch Prediction Complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()