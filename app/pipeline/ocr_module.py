# [수정 후: app/pipeline/ocr_module.py]
# (java_tls의 src/ocr/ocr_vl_module.py기반으로 수정)

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


# 🔴 [!!! 수정 !!!] 클래스 이름을 ver2의 기존 이름과 일치
class PaddleOCRModule:
    def __init__(self, use_gpu=False, enable_handwriting=True, supported_langs=None):
        """
        다국어 OCR 모듈 초기화

        Args:
            use_gpu: GPU 사용 여부
            enable_handwriting: 손글씨 인식 강화 (전처리 추가)
            supported_langs: 지원 언어 리스트 ['en', 'thai', 'korean', 'japan']
                            None이면 전부 지원
        """
        logger.info("=" * 60)
        logger.info("Initializing Multilingual OCR (Upgraded)...")
        logger.info("=" * 60)

        if supported_langs is None:
            supported_langs = ['en', 'thai', 'korean', 'japan']

        self.supported_langs = supported_langs
        self.use_gpu = use_gpu
        self.enable_handwriting = enable_handwriting

        # OCR 인스턴스를 lazy loading으로 (처음 사용할 때만 로드)
        self.ocr_instances = {}

        # 기본 영어는 미리 로드 (가장 자주 쓰임)
        logger.info("  📚 Loading English OCR (default)...")
        self.ocr_instances['en'] = self._create_ocr_instance('en')

        logger.info(f"  ✓ Multilingual OCR ready!")
        logger.info(f"  📖 Supported languages: {', '.join(supported_langs)}")
        logger.info(f"  🔧 Handwriting enhancement: {'Enabled' if enable_handwriting else 'Disabled'}")
        logger.info(f"  🚀 GPU acceleration: {'Enabled' if use_gpu else 'Disabled'}")
        logger.info(f"  💡 Other languages will be loaded on-demand")
        logger.info("=" * 60)

    def _create_ocr_instance(self, lang):
        """특정 언어의 OCR 인스턴스 생성"""
        return PaddleOCR(
            use_angle_cls=True,  # 텍스트 회전 보정
            lang=lang,
            use_gpu=self.use_gpu,
            show_log=False,
            # 손글씨 강화 옵션
            det_db_thresh=0.3,  # 텍스트 영역 감지 임계값 (낮을수록 작은 글씨도 잡음)
            det_db_box_thresh=0.5,  # 박스 신뢰도 임계값
        )

    def _get_ocr_instance(self, lang):
        """OCR 인스턴스 가져오기 (없으면 생성 - lazy loading)"""
        if lang not in self.ocr_instances:
            logger.info(f"  📥 Loading {lang.upper()} OCR model (first time)...")
            self.ocr_instances[lang] = self._create_ocr_instance(lang)
            logger.info(f"  ✓ {lang.upper()} OCR ready!")
        return self.ocr_instances[lang]

    def _detect_language_from_text(self, text):
        """
        OCR된 텍스트에서 언어 감지
        Returns: 'en', 'thai', 'korean', 'japan', 'mixed'
        """
        if not text or len(text) < 10:
            return 'en'  # 기본값

        # 유니코드 범위로 각 언어 문자 개수 세기
        thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
        korean_chars = len(re.findall(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]', text))
        japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF]', text))

        total_asian_chars = thai_chars + korean_chars + japanese_chars
        total_chars = len(text.replace(' ', '').replace('\n', ''))

        # 아시아 문자가 전체의 30% 이상이면 해당 언어
        if total_chars > 0:
            ratio = total_asian_chars / total_chars

            if ratio > 0.3:
                # 어느 언어가 가장 많은지 판단
                lang_scores = {
                    'thai': thai_chars,
                    'korean': korean_chars,
                    'japan': japanese_chars
                }
                detected = max(lang_scores, key=lang_scores.get)
                logger.info(f"  🔍 Language detected: {detected.upper()} ({ratio * 100:.1f}% Asian chars)")
                return detected

        return 'en'

    def _detect_language_from_image(self, image_path):
        """
        이미지에서 직접 언어 감지 (빠른 샘플 OCR)
        전략: 영어로 먼저 빠르게 OCR → 언어 판별
        """
        try:
            # 영어 OCR로 샘플 추출 (빠름)
            ocr_en = self._get_ocr_instance('en')
            result = ocr_en.ocr(str(image_path), cls=True)

            if result and result[0]:
                # 상위 5줄만 추출해서 언어 감지
                sample_text = '\n'.join([line[1][0] for line in result[0][:5]])
                detected = self._detect_language_from_text(sample_text)
                return detected
        except Exception as e:
            logger.warning(f"  ⚠️  Language detection failed: {e}")

        return 'en'  # 실패하면 기본값

    def _should_preprocess(self, image_path):
        """
        문서가 전처리가 필요한지 자동 판단 (품질 기반)
        """
        try:
            # 이미지 로드
            if isinstance(image_path, str):
                img = cv2.imread(image_path)
            else:
                img = image_path

            if img is None:
                return True  # 안전하게 전처리 적용

            # 그레이스케일 변환
            gray = cv2.cvtColor(img, cv.COLOR_BGR2GRAY)

            # 1. 선명도 측정 (Laplacian variance - 높을수록 선명)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            # 2. 대비 측정 (표준편차 - 높을수록 대비 좋음)
            contrast = gray.std()

            # 3. 밝기 측정
            brightness = gray.mean()

            # 품질 판단 임계값
            SHARPNESS_THRESHOLD = 100  # 선명도
            CONTRAST_THRESHOLD = 50  # 대비

            is_blurry = laplacian_var < SHARPNESS_THRESHOLD
            is_low_contrast = contrast < CONTRAST_THRESHOLD
            is_too_dark = brightness < 50
            is_too_bright = brightness > 230

            # 저품질 조건
            needs_preprocessing = is_blurry or is_low_contrast or is_too_dark or is_too_bright

            logger.info(f"  📊 이미지 품질 분석:")
            logger.info(f"     선명도: {laplacian_var:.1f} (임계값: {SHARPNESS_THRESHOLD})")
            logger.info(f"     대비: {contrast:.1f} (임계값: {CONTRAST_THRESHOLD})")
            logger.info(f"     밝기: {brightness:.1f}")

            if needs_preprocessing:
                logger.info(f"  🖊️  저품질/손글씨 감지 → 전처리 적용")
            else:
                logger.info(f"  ✨ 고품질 인쇄 감지 → 원본 사용 (전처리 스킵)")

            return needs_preprocessing

        except Exception as e:
            logger.warning(f"  ⚠️  품질 분석 실패: {e}, 안전하게 전처리 적용")
            return True  # 실패 시 안전하게 전처리 적용

    def _preprocess_for_handwriting(self, image_path):
        """
        손글씨 인식을 위한 이미지 전처리 (저품질 문서용)
        """
        try:
            # 이미지 로드
            if isinstance(image_path, str):
                img = cv2.imread(image_path)
            else:
                img = image_path  # 이미 numpy array인 경우

            if img is None:
                return None

            # 1. 그레이스케일 변환
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 2. 노이즈 제거 (가벼운 블러)
            denoised = cv2.GaussianBlur(gray, (3, 3), 0)

            # 3. 대비 증가 (CLAHE - 보수적 설정)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # 4. 부드러운 샤프닝 (과도한 샤프닝 방지)
            kernel = np.array([[0, -1, 0],
                               [-1, 5, -1],
                               [0, -1, 0]])  # 더 부드러운 커널
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            return sharpened

        except Exception as e:
            logger.error(f"  ⚠️  Handwriting preprocessing failed: {e}")
            return None

    def process_document(self, image_path, lang='auto'):
        """
        이미지에서 텍스트 + 레이아웃 추출 (다국어 지원)
        (java_tls의 OCRVLModule.process_document)
        """
        start_time = time.time()

        try:
            # Step 1: 언어 결정
            if lang == 'auto':
                logger.info(f"  🔍 Auto-detecting language...")
                detected_lang = self._detect_language_from_image(image_path)
            else:
                detected_lang = lang
                logger.info(f"  📝 Using specified language: {detected_lang.upper()}")

            # Step 2: 품질 기반 전처리 (스마트 전처리)
            processed_image = None
            if self.enable_handwriting:
                if self._should_preprocess(image_path):
                    processed_image = self._preprocess_for_handwriting(image_path)
                else:
                    processed_image = None  # 원본 사용

            # Step 3: 해당 언어 OCR 실행
            logger.info(f"  🚀 Processing with {detected_lang.upper()} OCR...")
            ocr = self._get_ocr_instance(detected_lang)

            # 🔴 [수정] cls=False (ver2 원본의 안정적인 설정 유지)
            ocr_cls_param = False

            if processed_image is not None:
                result = ocr.ocr(processed_image, cls=ocr_cls_param)
            else:
                result = ocr.ocr(str(image_path), cls=ocr_cls_param)

            if not result or not result[0]:
                return {
                    "full_text": "",
                    "layout": {},
                    "confidence": 0.0,
                    "processing_time": time.time() - start_time,
                    "detected_language": detected_lang,
                    "error": "No text detected"
                }

            # Step 4: 텍스트 추출 및 레이아웃 파싱
            full_text = self._extract_text(result)
            layout = self._parse_layout(result)
            confidence = self._calc_confidence(result)

            logger.info(f"  ✓ OCR complete! Confidence: {confidence:.2%}")

            return {
                "full_text": full_text,
                "layout": layout,
                "confidence": confidence,
                "processing_time": time.time() - start_time,
                "detected_language": detected_lang
            }

        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return {
                "full_text": "",
                "layout": {},
                "confidence": 0.0,
                "processing_time": time.time() - start_time,
                "detected_language": lang if lang != 'auto' else 'en',
                "error": str(e)
            }

    def _extract_text(self, result):
        """전체 텍스트 추출 (ver2의 안정적인 공백 ' ' join 방식 유지)"""
        lines = []
        for line in result[0]:
            bbox, (text, conf) = line
            lines.append(text)
        # 🔴 [수정] \n 대신 ' ' 공백으로 연결 (ver2원본 방식)
        return ' '.join(lines)

    def _parse_layout(self, result):
        """
        레이아웃 정보 파싱 (INTERFACE.md기준)
        - 제목 식별
        - 키-값 쌍 감지
        - 테이블 감지
        - 모든 텍스트 박스 정보 (all_boxes)
        """
        lines = result[0]

        layout = {
            "title": None,
            "sections": [],
            "all_boxes": [],  # 새로 추가: 모든 텍스트+위치+신뢰도
            "features": {}
        }

        # 0. 모든 텍스트 박스 저장 (필터링 없이 전부)
        for line in lines:
            bbox, (text, conf) = line
            x1, y1 = bbox[0]  # 좌상단
            x2, y2 = bbox[2]  # 우하단

            layout["all_boxes"].append({
                "text": text,
                "bbox": [float(x1), float(y1), float(x2), float(y2)],  # [left, top, right, bottom]
                "confidence": float(conf),
                "width": float(x2 - x1),
                "height": float(y2 - y1)
            })

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

            if width < 50:
                continue

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
        numeric_lines = sum(1 for line in lines if any(c.isdigit() for c in line[1][0]))
        return numeric_lines > len(lines) * 0.3

    def _calc_confidence(self, result):
        """평균 신뢰도 계산"""
        confidences = [line[1][1] for line in result[0]]
        return sum(confidences) / len(confidences) if confidences else 0.0

    def process_pdf_multipage(self, pdf_path, lang='auto', max_pages=3):
        """
        PDF 파일의 여러 페이지 처리
        (java_tls의 OCRVLModule.process_pdf_multipage)
        """
        start_time = time.time()

        logger.info(f"\n📄 Processing PDF: {Path(pdf_path).name}")

        try:
            # PDF 열기
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            logger.info(f"  📊 Total pages: {total_pages}")

            # 처리할 페이지 수 결정
            if total_pages <= 3:
                pages_to_process = total_pages
                logger.info(f"  ✅ Processing all {total_pages} pages")
            else:
                pages_to_process = max_pages
                logger.info(f"  📌 Processing first {max_pages} pages (out of {total_pages})")

            all_texts = []
            all_confidences = []
            first_page_layout = None
            detected_lang = None

            # 임시 디렉토리 생성
            with tempfile.TemporaryDirectory() as temp_dir:
                # 각 페이지를 순차적으로 처리
                for page_num in range(pages_to_process):
                    logger.info(f"\n  📄 Processing page {page_num + 1}/{pages_to_process}...")

                    try:
                        # 페이지를 이미지로 변환
                        page = doc[page_num]
                        pix = page.get_pixmap()

                        # 임시 이미지 파일로 저장
                        temp_image = os.path.join(temp_dir, f"page_{page_num}.png")
                        pix.save(temp_image)

                        # OCR 처리 (이미지 처리 함수 호출)
                        result = self.process_document(temp_image, lang=lang)

                        if 'error' not in result:
                            # 🔴 [수정] 페이지 번호와 ' '로 join된 텍스트 저장
                            page_text = f"[Page {page_num + 1}] {result['full_text']}"
                            all_texts.append(page_text)
                            all_confidences.append(result['confidence'])

                            # 첫 페이지의 레이아웃과 언어 정보 저장
                            if page_num == 0:
                                first_page_layout = result['layout']
                                detected_lang = result.get('detected_language', 'en')

                            logger.info(f"    ✓ Page {page_num + 1} done (confidence: {result['confidence']:.2%})")
                        else:
                            logger.warning(f"    ⚠️  Page {page_num + 1} OCR failed: {result['error']}")
                            all_texts.append(f"[Page {page_num + 1}] [OCR Error: {result['error']}]")
                            all_confidences.append(0.0)

                        del pix
                        del page
                        if os.path.exists(temp_image):
                            os.remove(temp_image)

                    except Exception as page_error:
                        logger.error(f"    ❌ Error processing page {page_num + 1}: {page_error}")
                        all_texts.append(f"[Page {page_num + 1}] [Error: {str(page_error)}]")
                        all_confidences.append(0.0)

            doc.close()

            if not all_texts:
                # 🔴 [!!! 수정 !!!] ... 대신 완전한 에러 딕셔너리 반환
                logger.warning(f"PDF processing failed: No text extracted from {Path(pdf_path).name}")
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

            # 🔴 [수정] PDF 페이지 join 방식도 ' ' (공백 두 개)로 통일
            combined_text = "  ".join(all_texts)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

            logger.info(f"\n  ✅ PDF processing complete!")
            logger.info(f"     Processed: {len(all_texts)}/{total_pages} pages")
            logger.info(f"     Average confidence: {avg_confidence:.2%}")

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
            logger.error(f"\n  ❌ PDF processing failed: {error_msg}")
            # (오류 처리)
            return {
                "full_text": "",
                "layout": {},
                "confidence": 0.0,
                "processing_time": time.time() - start_time,
                "detected_language": 'en',
                "total_pages": 0,
                "processed_pages": 0,
                "error": f"PDF processing error: {error_msg}"
            }