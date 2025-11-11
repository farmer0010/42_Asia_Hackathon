import os
import logging
import time
import json
import re
import tempfile
from pathlib import Path
from paddleocr import PaddleOCR
import fitz  # PyMuPDF
import cv2
import numpy as np

# 로거 설정
logger = logging.getLogger(__name__)


# 🔴 [유지] 클래스 이름을 ver2의 기존 이름과 일치
class PaddleOCRModule:
    def __init__(self, use_gpu=False, enable_handwriting=True, supported_langs=None):
        """
        다국어 OCR 모듈 초기화 (Upgraded)
        """
        logger.info("=" * 60)
        logger.info("Initializing Multilingual OCR (Upgraded)...")
        logger.info("=" * 60)

        if supported_langs is None:
            supported_langs = ['en', 'thai', 'korean', 'japan']

        self.supported_langs = supported_langs
        self.use_gpu = use_gpu
        self.enable_handwriting = enable_handwriting
        self.ocr_instances = {}

        logger.info("  📚 Loading English OCR (default)...")
        self.ocr_instances['en'] = self._create_ocr_instance('en')

        logger.info(f"  ✓ Multilingual OCR ready!")
        logger.info(f"  📖 Supported languages: {', '.join(supported_langs)}")
        logger.info(f"  🔧 Handwriting enhancement: {'Enabled' if enable_handwriting else 'Disabled'}")
        logger.info(f"  🚀 GPU acceleration: {'Enabled' if use_gpu else 'Disabled'}")
        logger.info("=" * 60)

    def _create_ocr_instance(self, lang):
        """특정 언어의 OCR 인스턴스 생성"""
        return PaddleOCR(
            use_angle_cls=True,  # 텍스트 회전 보정
            lang=lang,
            use_gpu=self.use_gpu,
            show_log=False,
            det_db_thresh=0.3,
            det_db_box_thresh=0.5,
        )

    def _get_ocr_instance(self, lang):
        """OCR 인스턴스 가져오기 (lazy loading)"""
        if lang not in self.ocr_instances:
            logger.info(f"  📥 Loading {lang.upper()} OCR model (first time)...")
            self.ocr_instances[lang] = self._create_ocr_instance(lang)
            logger.info(f"  ✓ {lang.upper()} OCR ready!")
        return self.ocr_instances[lang]

    def _detect_language_from_text(self, text):
        """OCR된 텍스트에서 언어 감지"""
        if not text or len(text) < 10:
            return 'en'

        thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
        korean_chars = len(re.findall(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]', text))
        japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF]', text))

        total_asian_chars = thai_chars + korean_chars + japanese_chars
        total_chars = len(text.replace(' ', '').replace('\n', ''))

        if total_chars > 0:
            ratio = total_asian_chars / total_chars
            if ratio > 0.3:
                lang_scores = {'thai': thai_chars, 'korean': korean_chars, 'japan': japanese_chars}
                detected = max(lang_scores, key=lang_scores.get)
                logger.info(f"  🔍 Language detected: {detected.upper()} ({ratio * 100:.1f}% Asian chars)")
                return detected
        return 'en'

    def _detect_language_from_image(self, image_path):
        """이미지에서 직접 언어 감지 (빠른 샘플 OCR)"""
        try:
            ocr_en = self._get_ocr_instance('en')
            result = ocr_en.ocr(str(image_path), cls=True)
            if result and result[0]:
                sample_text = '\n'.join([line[1][0] for line in result[0][:5]])
                return self._detect_language_from_text(sample_text)
        except Exception as e:
            logger.warning(f"  ⚠️  Language detection failed: {e}")
        return 'en'

    def _should_preprocess(self, image_path):
        """품질 기반 자동 전처리 판단"""
        try:
            if isinstance(image_path, str):
                img = cv2.imread(image_path)
            else:
                img = image_path
            if img is None:
                return True

            # 🔴 [!!! 오류 수정 !!!] 'cv.' -> 'cv2.'
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            contrast = gray.std()
            brightness = gray.mean()

            SHARPNESS_THRESHOLD = 100
            CONTRAST_THRESHOLD = 50
            is_blurry = laplacian_var < SHARPNESS_THRESHOLD
            is_low_contrast = contrast < CONTRAST_THRESHOLD
            is_too_dark = brightness < 50
            is_too_bright = brightness > 230
            needs_preprocessing = is_blurry or is_low_contrast or is_too_dark or is_too_bright

            logger.info(f"  📊 이미지 품질 분석: 선명도({laplacian_var:.1f}), 대비({contrast:.1f}), 밝기({brightness:.1f})")
            if needs_preprocessing:
                logger.info(f"  🖊️  저품질/손글씨 감지 → 전처리 적용")
            else:
                logger.info(f"  ✨ 고품질 인쇄 감지 → 원본 사용 (전처리 스킵)")
            return needs_preprocessing
        except Exception as e:
            logger.warning(f"  ⚠️  품질 분석 실패: {e}, 안전하게 전처리 적용")
            return True

    def _preprocess_for_handwriting(self, image_path):
        """손글씨 인식을 위한 이미지 전처리"""
        try:
            if isinstance(image_path, str):
                img = cv2.imread(image_path)
            else:
                img = image_path
            if img is None:
                return None

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.GaussianBlur(gray, (3, 3), 0)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            return sharpened
        except Exception as e:
            logger.error(f"  ⚠️  Handwriting preprocessing failed: {e}")
            return None

    def process_document(self, image_path, lang='auto'):
        """단일 이미지 텍스트 + 레이아웃 추출"""
        start_time = time.time()
        try:
            if lang == 'auto':
                logger.info(f"  🔍 Auto-detecting language...")
                detected_lang = self._detect_language_from_image(image_path)
            else:
                detected_lang = lang
                logger.info(f"  📝 Using specified language: {detected_lang.upper()}")

            processed_image = None
            if self.enable_handwriting:
                if self._should_preprocess(image_path):
                    processed_image = self._preprocess_for_handwriting(image_path)

            logger.info(f"  🚀 Processing with {detected_lang.upper()} OCR...")
            ocr = self._get_ocr_instance(detected_lang)
            ocr_cls_param = False  # 🔴 [유지] ver2의 안정적인 cls=False 고정

            if processed_image is not None:
                result = ocr.ocr(processed_image, cls=ocr_cls_param)
            else:
                result = ocr.ocr(str(image_path), cls=ocr_cls_param)

            if not result or not result[0]:
                return {
                    "full_text": "", "layout": {}, "confidence": 0.0,
                    "processing_time": time.time() - start_time,
                    "detected_language": detected_lang, "error": "No text detected"
                }

            full_text = self._extract_text(result)
            layout = self._parse_layout(result)
            confidence = self._calc_confidence(result)
            logger.info(f"  ✓ OCR complete! Confidence: {confidence:.2%}")

            return {
                "full_text": full_text, "layout": layout, "confidence": confidence,
                "processing_time": time.time() - start_time, "detected_language": detected_lang
            }
        except Exception as e:
            logger.error(f"  ❌ Error in process_document: {e}", exc_info=True)
            return {
                "full_text": "", "layout": {}, "confidence": 0.0,
                "processing_time": time.time() - start_time,
                "detected_language": lang if lang != 'auto' else 'en', "error": str(e)
            }

    def _extract_text(self, result):
        """텍스트 추출 (ver2의 ' ' join 방식 유지)"""
        lines = [line[1][0] for line in result[0]]
        return ' '.join(lines)

    def _parse_layout(self, result):
        """레이아웃 정보 파싱 (INTERFACE.md기준)"""
        lines = result[0]
        layout = {"title": None, "sections": [], "all_boxes": [], "features": {}}

        for line in lines:
            bbox, (text, conf) = line
            x1, y1 = bbox[0];
            x2, y2 = bbox[2]
            layout["all_boxes"].append({
                "text": text,
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "confidence": float(conf), "width": float(x2 - x1), "height": float(y2 - y1)
            })

        for box in layout["all_boxes"]:
            if box["bbox"][1] < 100 and box["width"] > 150 and box["height"] > 15:
                layout["title"] = box["text"]
                break

        key_value_count = 0
        for box in layout["all_boxes"]:
            if box["width"] < 50: continue
            if ':' in box["text"] or any(
                    kw in box["text"].lower() for kw in ['date', 'no', 'total', 'amount', 'invoice']):
                key_value_count += 1
                layout["sections"].append({
                    "type": "key_value", "text": box["text"], "position": [box["bbox"][0], box["bbox"][1]]
                })

        layout["features"] = {
            "has_table": self._detect_table(lines),
            "num_key_value_pairs": key_value_count,
            "text_density": len(lines) / 100.0,
            "total_lines": len(lines)
        }
        return layout

    def _detect_table(self, lines):
        """테이블 존재 여부 감지"""
        numeric_lines = sum(1 for line in lines if any(c.isdigit() for c in line[1][0]))
        return numeric_lines > len(lines) * 0.3

    def _calc_confidence(self, result):
        """평균 신뢰도 계산"""
        confidences = [line[1][1] for line in result[0]]
        return sum(confidences) / len(confidences) if confidences else 0.0

    def process_pdf_multipage(self, pdf_path, lang='auto', max_pages=3):
        """PDF 여러 페이지 처리"""
        start_time = time.time()
        logger.info(f"\n📄 Processing PDF: {Path(pdf_path).name}")
        total_pages = 0
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            logger.info(f"  📊 Total pages: {total_pages}")

            pages_to_process = total_pages if total_pages <= 3 else max_pages
            if total_pages > max_pages:
                logger.info(f"  📌 Processing first {pages_to_process} pages (out of {total_pages})")
            else:
                logger.info(f"  ✅ Processing all {pages_to_process} pages")

            all_texts = [];
            all_confidences = []
            first_page_layout = None;
            detected_lang = None

            with tempfile.TemporaryDirectory() as temp_dir:
                for page_num in range(pages_to_process):
                    logger.info(f"\n  📄 Processing page {page_num + 1}/{pages_to_process}...")
                    try:
                        page = doc[page_num]
                        pix = page.get_pixmap()
                        temp_image = os.path.join(temp_dir, f"page_{page_num}.png")
                        pix.save(temp_image)

                        result = self.process_document(temp_image, lang=lang)

                        if 'error' not in result:
                            page_text = f"[Page {page_num + 1}] {result['full_text']}"
                            all_texts.append(page_text)
                            all_confidences.append(result['confidence'])
                            if page_num == 0:
                                first_page_layout = result['layout']
                                detected_lang = result.get('detected_language', 'en')
                            logger.info(f"    ✓ Page {page_num + 1} done (confidence: {result['confidence']:.2%})")
                        else:
                            logger.warning(f"    ⚠️  Page {page_num + 1} OCR failed: {result['error']}")
                            all_texts.append(f"[Page {page_num + 1}] [OCR Error: {result['error']}]")
                            all_confidences.append(0.0)

                        del pix;
                        del page
                        if os.path.exists(temp_image): os.remove(temp_image)
                    except Exception as page_error:
                        logger.error(f"    ❌ Error processing page {page_num + 1}: {page_error}", exc_info=True)
                        all_texts.append(f"[Page {page_num + 1}] [Error: {str(page_error)}]")
                        all_confidences.append(0.0)
            doc.close()

            if not all_texts:
                logger.warning(f"PDF processing failed: No text extracted from {Path(pdf_path).name}")
                # 🔴 [!!! 수정 !!!] SyntaxError '...' 대신 완전한 에러 Dict 반환
                return {
                    "full_text": "",
                    "layout": {},
                    "confidence": 0.0,
                    "processing_time": time.time() - start_time,
                    "detected_language": 'en',
                    "total_pages": total_pages,
                    "processed_pages": 0,
                    "error": "No pages could be processed"
                }

            combined_text = "  ".join(all_texts)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            logger.info(f"\n  ✅ PDF processing complete!")

            return {
                "full_text": combined_text,
                "layout": first_page_layout or {},
                "confidence": avg_confidence,
                "processing_time": time.time() - start_time,
                "detected_language": detected_lang or 'en',
                "total_pages": total_pages,
                "processed_pages": len(all_texts)
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"\n  ❌ PDF processing failed: {error_msg}", exc_info=True)
            return {
                "full_text": "", "layout": {}, "confidence": 0.0,
                "processing_time": time.time() - start_time,
                "detected_language": 'en', "total_pages": total_pages, "processed_pages": 0,
                "error": f"PDF processing error: {error_msg}"
            }