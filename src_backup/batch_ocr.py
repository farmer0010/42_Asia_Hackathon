# src/batch_ocr.py

import argparse
from pathlib import Path
from ocr_module import OCRModule
from tqdm import tqdm
import json


def main():
    print("=" * 60)
    print("Batch OCR Processing")
    print("=" * 60)
    
    # 1. 명령줄 인자 설정
    parser = argparse.ArgumentParser(description='Batch OCR processing')
    parser.add_argument('--input', required=True, help='Input directory')
    parser.add_argument('--output', required=True, help='Output JSON file')
    args = parser.parse_args()
    
    print(f"\nInput directory: {args.input}")
    print(f"Output file: {args.output}")
    
    # 2. OCR 초기화
    print("\nInitializing OCR module...")
    ocr = OCRModule()
    
    # 3. 파일 스캔
    print(f"\nScanning files in {args.input}...")
    input_path = Path(args.input)
    
    # 모든 이미지/PDF 파일 찾기
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf']:
        files.extend(input_path.glob(ext))
    
    if not files:
        print("Error: No files found!")
        return
    
    print(f"Found {len(files)} files")
    
    # 4. OCR 처리
    print("\nProcessing files...")
    results = {}
    
    for file in tqdm(files, desc="OCR Progress"):
        try:
            result = ocr.extract_text(str(file))
            results[file.name] = result
        except Exception as e:
            print(f"\nError processing {file.name}: {e}")
            results[file.name] = {
                'text': '',
                'confidence': 0.0,
                'error': str(e)
            }
    
    # 5. 결과 저장
    print(f"\nSaving results to {args.output}...")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 6. 통계 출력
    print("\n" + "=" * 60)
    print("Processing Complete!")
    print("=" * 60)
    print(f"Total files: {len(files)}")
    print(f"Successful: {len([r for r in results.values() if 'error' not in r])}")
    print(f"Failed: {len([r for r in results.values() if 'error' in r])}")
    print(f"Output saved to: {args.output}")
    print("=" * 60)


if __name__ == '__main__':
    main()