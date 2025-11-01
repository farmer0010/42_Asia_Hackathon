import sys
sys.path.append('srcs')

from ocr_vl_module import OCRVLModule
from pathlib import Path
import json
import argparse
from tqdm import tqdm

def main():
    parser = argparse.ArgumentParser(description='Batch OCR-VL processing')
    parser.add_argument('--input', required=True, help='Input directory')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('--gpu', action='store_true', help='Use GPU')
    args = parser.parse_args()
    
    # OCR-VL 초기화
    print("Initializing OCR-VL...")
    ocr_vl = OCRVLModule(use_gpu=args.gpu)
    
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
    results = {}
    errors = []
    
    for file_path in tqdm(files, desc="Processing"):
        try:
            result = ocr_vl.process_document(str(file_path))
            
            if 'error' not in result:
                results[file_path.name] = result
            else:
                errors.append({
                    'file': file_path.name,
                    'error': result['error']
                })
        
        except Exception as e:
            print(f"\n❌ Error processing {file_path.name}: {e}")
            errors.append({
                'file': file_path.name,
                'error': str(e)
            })
    
    # 결과 저장
    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 에러 저장 (있으면)
    if errors:
        error_path = output_path.parent / f"{output_path.stem}_errors.json"
        with open(error_path, 'w', encoding='utf-8') as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)
    
    # 통계
    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Total files: {len(files)}")
    print(f"Successful: {len(results)}")
    print(f"Errors: {len(errors)}")
    
    if results:
        avg_conf = sum(r['confidence'] for r in results.values()) / len(results)
        avg_time = sum(r['processing_time'] for r in results.values()) / len(results)
        print(f"\nAverage confidence: {avg_conf:.2%}")
        print(f"Average processing time: {avg_time:.2f}s")
    
    print(f"\n✓ Results saved to: {output_path}")
    if errors:
        print(f"✓ Errors saved to: {error_path}")

if __name__ == "__main__":
    main()