# src/ocr_vl_module.py

from paddleocr import PaddleOCR
import time
from pathlib import Path
import json

class OCRVLModule:
    def __init__(self, use_gpu=False):
        """PaddleOCR 초기화"""
        print("Initializing PaddleOCR...")
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=use_gpu,
            show_log=False
        )
        print("OCR ready!")
    
    def process_document(self, image_path):
        """
        이미지에서 텍스트 + 레이아웃 추출
        
        Returns:
            dict: {
                "full_text": str,
                "layout": dict,
                "confidence": float,
                "processing_time": float
            }
        """
        start_time = time.time()
        
        try:
            # OCR 실행
            result = self.ocr.ocr(str(image_path), cls=True)
            
            if not result or not result[0]:
                return {
                    "full_text": "",
                    "layout": {},
                    "confidence": 0.0,
                    "processing_time": time.time() - start_time,
                    "error": "No text detected"
                }
            
            # 텍스트 추출
            full_text = self._extract_text(result)
            
            # 레이아웃 파싱
            layout = self._parse_layout(result)
            
            # 평균 신뢰도
            confidence = self._calc_confidence(result)
            
            return {
                "full_text": full_text,
                "layout": layout,
                "confidence": confidence,
                "processing_time": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "full_text": "",
                "layout": {},
                "confidence": 0.0,
                "processing_time": time.time() - start_time,
                "error": str(e)
            }
    
    def _extract_text(self, result):
        """전체 텍스트 추출"""
        lines = []
        for line in result[0]:
            bbox, (text, conf) = line
            lines.append(text)
        return '\n'.join(lines)
    
    def _parse_layout(self, result):
        """
        레이아웃 정보 파싱
        - 제목 식별
        - 키-값 쌍 감지
        - 테이블 감지
        """
        lines = result[0]
        
        layout = {
            "title": None,
            "sections": [],
            "features": {}
        }
        
        # 1. 제목 찾기 (Y < 100, W > 150, H > 15)
        for line in lines:
            bbox, (text, conf) = line
            x1, y1 = bbox[0]  # 좌상단
            x2, y2 = bbox[2]  # 우하단
            width = x2 - x1
            height = y2 - y1
            
            if y1 < 100 and width > 150 and height > 15:
                layout["title"] = text
                break  # 첫 번째 제목만
        
        # 2. 키-값 쌍 찾기
        key_value_count = 0
        for line in lines:
            bbox, (text, conf) = line
            x1, y1 = bbox[0]
            x2, y2 = bbox[2]
            width = x2 - x1
            
            # 작은 텍스트는 스킵 (체크박스 등)
            if width < 50:
                continue
            
            # 키-값 쌍 감지
            if ':' in text or any(kw in text.lower() for kw in ['date', 'no', 'total', 'amount', 'invoice']):
                key_value_count += 1
                layout["sections"].append({
                    "type": "key_value",
                    "text": text,
                    "position": [x1, y1]
                })
        
        # 3. 특징 추출
        layout["features"] = {
            "has_table": self._detect_table(lines),
            "num_key_value_pairs": key_value_count,
            "text_density": len(lines) / 100.0,
            "total_lines": len(lines)
        }
        
        return layout
    
    def _detect_table(self, lines):
        """테이블 존재 여부 감지"""
        # 숫자가 많으면 테이블 가능성
        numeric_lines = sum(1 for line in lines if any(c.isdigit() for c in line[1][0]))
        return numeric_lines > len(lines) * 0.3
    
    def _calc_confidence(self, result):
        """평균 신뢰도 계산"""
        confidences = [line[1][1] for line in result[0]]
        return sum(confidences) / len(confidences) if confidences else 0.0

if __name__ == "__main__":
    # 빠른 단일 파일 테스트용
    print("Quick test...")
    
    ocr = OCRVLModule()
    result = ocr.process_document("test_samples/sample4.jpg")
    
    print(f"✓ Confidence: {result['confidence']:.2%}")
    print(f"✓ Title: {result['layout'].get('title')}")
    print(f"✓ Text preview: {result['full_text'][:100]}...")
    print("\nFor batch processing, use: python srcs/batch_ocr_vl.py")