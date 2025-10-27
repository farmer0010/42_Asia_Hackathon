# src/ocr_module.py

from paddleocr import PaddleOCR
import cv2
import numpy as np
from pathlib import Path
import time
import logging
import os  # pdf2image 임시 폴더용

log = logging.getLogger(__name__)


class OCRModule:

    def __init__(self, lang='en', use_gpu=False):
        log.info(f"Initializing OCR module (language: {lang})...")

        self.ocr = PaddleOCR(
            use_angle_cls=False,
            lang=lang,
            use_gpu=use_gpu,
            show_log=False
        )

        log.info("OCR module ready.")

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
            # PDF 파일인 경우, 이미지로 먼저 변환
            if Path(file_path).suffix.lower() == '.pdf':
                log.info(f"Converting PDF to image: {file_path}")
                file_path = self._pdf_to_image(file_path)
                log.info(f"Converted PDF to image at: {file_path}")

            # PaddleOCR은 전처리된 이미지보다 원본에서 더 잘 동작할 수 있습니다.
            # 원본 이미지 경로를 직접 사용합니다.
            # img = self.preprocess_image(file_path) 

            result = self.ocr.ocr(str(file_path), cls=False)

            if not result or not result[0]:
                log.warning(f"No text detected in {file_path}")
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

            full_text = '\n'.join(lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            log.info(f"OCR successful for {file_path}. Length: {len(full_text)}, Confidence: {avg_confidence:.2%}")

            return {
                'text': full_text,
                'confidence': avg_confidence,
                'processing_time': time.time() - start_time
            }

        except Exception as e:
            log.error(f"OCR processing failed for {file_path}. Error: {e}", exc_info=True)
            return {
                'text': '',
                'confidence': 0.0,
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
        finally:
            # PDF에서 변환된 임시 이미지 파일인 경우 삭제
            if 'temp_image_path' in locals() and os.path.exists(temp_image_path):
                os.remove(temp_image_path)
                log.info(f"Removed temp image: {temp_image_path}")

    def _pdf_to_image(self, pdf_path):
        """(first page only)"""
        from pdf2image import convert_from_path

        # PDF를 /tmp 임시 폴더에 고유한 이름의 이미지로 변환
        temp_image_dir = Path("/tmp/pdf_images")
        temp_image_dir.mkdir(parents=True, exist_ok=True)

        # 고유한 파일 이름 생성 (worker.py에서 생성한 이름을 그대로 사용)
        pdf_stem = Path(pdf_path).stem
        temp_image_path = temp_image_dir / f"{pdf_stem}.png"

        images = convert_from_path(
            pdf_path,
            first_page=1,
            last_page=1,
            output_folder=temp_image_dir,
            output_file=pdf_stem,
            fmt='png'
        )

        if images and os.path.exists(temp_image_path):
            return str(temp_image_path.resolve())
        else:
            log.error(f"PDF to image conversion failed for: {pdf_path}")
            raise Exception("PDF to image conversion failed")