# src/ocr_module.py

from paddleocr import PaddleOCR
import cv2
import numpy as np
from pathlib import Path
import time

class OCRModule:
    
    def __init__(self, lang='en', use_gpu=False):
        print(f"Initializing OCR module (language: {lang})...")
        
        self.ocr = PaddleOCR(
            use_angle_cls=False,
            lang=lang,
            use_gpu=use_gpu,
            show_log=False
        )
        
        print("OCR module ready\n")
    
    def preprocess_image(self, image_path):
        img = cv2.imread(str(image_path))
        
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        return enhanced
    
    def extract_text(self, file_path):

        start_time = time.time()
        
        try:
            if Path(file_path).suffix.lower() == '.pdf':
                file_path = self._pdf_to_image(file_path)
            

            img = self.preprocess_image(file_path)
            
            result = self.ocr.ocr(img, cls=False)
            
            if not result or not result[0]:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'processing_time': time.time() - start_time,
                    'error': 'No text detected'
                }
            
            lines = []
            confidences = []
            
            for line in result[0]:
                bbox, (text, conf) = line
                lines.append(text)
                confidences.append(conf)
            
            return {
                'text': '\n'.join(lines),
                'confidence': sum(confidences) / len(confidences) if confidences else 0.0,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            return {
                'text': '',
                'confidence': 0.0,
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    def _pdf_to_image(self, pdf_path):
        """(first page only)"""
        from pdf2image import convert_from_path
        
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        temp_path = f"/tmp/{Path(pdf_path).stem}.png"
        images[0].save(temp_path, 'PNG')
        
        return temp_path


if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("OCR Module Test")
    print("=" * 60)
    
    # Initialize OCR
    ocr = OCRModule(lang='en')
    
    # Find test files
    test_dir = Path("test_samples")
    
    if not test_dir.exists():
        print(f"Error: {test_dir} directory not found")
        exit(1)
    
    # Collect image files
    test_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf']:
        test_files.extend(test_dir.glob(ext))
    
    if not test_files:
        print(f"Error: No images found in {test_dir}")
        print("Please add sample images to test_samples/ directory")
        exit(1)
    
    print(f"\nFound {len(test_files)} files\n")
    
    # Process each file and collect results
    results = []
    total_time = 0
    total_confidence = 0
    
    for i, file_path in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] {file_path.name}")
        print("-" * 60)
        
        result = ocr.extract_text(str(file_path))
        result['filename'] = file_path.name
        results.append(result)
        
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Confidence: {result['confidence']:.2%}")
            print(f"Processing time: {result['processing_time']:.2f}s")
            print(f"Text length: {len(result['text'])} characters")
            print(f"\nExtracted text:")
            print(result['text'][:300])
            if len(result['text']) > 300:
                print("...")
            
            total_time += result['processing_time']
            total_confidence += result['confidence']
        
        print("\n")
    
    # Calculate statistics
    success_count = len([r for r in results if 'error' not in r])
    avg_confidence = total_confidence / success_count if success_count > 0 else 0
    avg_time = total_time / success_count if success_count > 0 else 0
    
    # Save results to JSON
    Path("outputs").mkdir(exist_ok=True)
    with open("outputs/ocr_test_results.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total files: {len(test_files)}")
    print(f"Success: {success_count}")
    print(f"Failed: {len(test_files) - success_count}")
    print(f"Average confidence: {avg_confidence:.2%}")
    print(f"Average processing time: {avg_time:.2f}s")
    print(f"\nResults saved to: outputs/ocr_test_results.json")
    print("=" * 60)
