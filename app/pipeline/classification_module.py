import os
from app.config import settings
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast
import torch
import logging

# 로거 설정
logger = logging.getLogger(__name__)


class DocumentClassifier:
    def __init__(self):
        # 1. 모델 경로 설정 (docker-compose.yml의 볼륨과 일치)
        # 우리는 'classifier'라는 이름의 폴더를 마운트할 것입니다.
        MODEL_PATH = settings.MODEL_PATH

        # 2. 장치 설정: Docker 컨테이너 내에서는 CPU가 가장 안정적입니다.
        # (ocr_module.py가 use_gpu=False로 설정한 것과 같은 원리)
        self.device = "cpu"

        logger.info(f"분류 모델 로딩 시작. 경로: {MODEL_PATH}, 장치: {self.device}")

        try:
            # 3. 모델 및 토크나이저 로드 (Hugging Face Transformers 방식)
            self.model = DistilBertForSequenceClassification.from_pretrained(MODEL_PATH).to(self.device)
            self.tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_PATH)

            # 4. 분류 클래스 이름(라벨) 로드 (예: 'invoice', 'report'...)
            self.id2label = self.model.config.id2label
            self.class_names = list(self.id2label.values())

            logger.info(f"분류 모델 로딩 성공. 클래스: {self.class_names}")

        except Exception as e:
            logger.error(f"'{MODEL_PATH}'에서 모델 로딩 실패! '/models' 폴더에 'classifier' 디렉토리를 복사했는지 확인하세요.")
            logger.error(f"오류: {e}")
            raise RuntimeError(f"모델 로딩 실패: {e}")

    def predict(self, text: str):
        """
        입력된 텍스트를 기반으로 문서 유형과 신뢰도 점수를 반환합니다.
        """
        if not text:
            logger.warning("분류기(Classifier)에 빈 텍스트가 입력되었습니다.")
            return "unknown", 0.0

        try:
            # 1. 텍스트를 토큰화 (모델이 이해하는 숫자로 변경)
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            ).to(self.device)

            # 2. 모델 예측
            with torch.no_grad():
                logits = self.model(**inputs).logits

            # 3. 결과 계산 (가장 확률이 높은 클래스 찾기)
            probs = torch.softmax(logits, dim=1)
            confidence, predicted_class_id = torch.max(probs, dim=1)

            # 4. 숫자 ID를 실제 문자열 라벨로 변환
            doc_type = self.id2label[predicted_class_id.item()]
            confidence_score = confidence.item()

            return doc_type, confidence_score

        except Exception as e:
            logger.error(f"분류 예측 중 오류 발생: {e}")
            return "error", 0.0