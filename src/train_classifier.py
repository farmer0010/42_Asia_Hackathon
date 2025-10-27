"""
# 명령어 실행법
python src/train_classifier.py \
  --labels hackathon_dataset/training_set/labels.csv \
  --ocr outputs/training_ocr.json \
  --output models/classifier
"""

import argparse
from pathlib import Path
from classification_module import DocumentClassifier

def main():
    print("Train Classification Model")

    # 1. 명령줄 인자 설정
    parser = argparse.ArgumentParser(description='Train document classifier')
    parser.add_argument('--labels', required=True, help='Path to labels.csv')
    parser.add_argument('--ocr', required=True, help='Path to OCR results JSON')
    parser.add_argument('--output', default='models/classifier', help='Output directory')
    args = parser.parse_args()
    
    print(f"\nInput files:")
    print(f"  Labels CSV: {args.labels}")
    print(f"  OCR Results: {args.ocr}")
    print(f"  Output dir: {args.output}")

    # 2. 파일 존재 확인
    if not Path(args.labels).exists():
        print(f"Error: {args.labels} not found!")
        return
    
    if not Path(args.ocr).exists():
        print(f"Error: {args.ocr} not found!")
        return
    
    print("\nAll input files found!")

    # 3. 분류기 초기화
    print("\nInitializing classifier...")
    classifier = DocumentClassifier()
    
    # 4. 학습 실행!
    classifier.train(
        labels_csv_path=args.labels,
        ocr_results_path=args.ocr,
        output_dir=args.output
    )
    
    print("\n" + "=" * 60)
    print("Classification model training complete!")
    print(f"Model saved to: {args.output}")
    print("=" * 60)

if __name__ == '__main__':
    main()