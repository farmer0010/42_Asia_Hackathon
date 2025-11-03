# D:\42_asia-hackathon\42_Asia_Hackathon-backend\app\pipeline\classification_module.py
# (기반: ocr_ver.2/srcs/classification_module.py)

import os
import joblib
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np

# 🔴 [핵심 1] docker-compose.yml의 환경 변수(MODEL_PATH)를 읽어오기 위해 import
from app.config import settings
from ..logger_config import setup_logging

log = setup_logging()

# 🔴 [핵심 2] ocr_ver.2의 "./models/classifier" 대신,
#           docker-compose.yml과 연동되는 'settings.MODEL_PATH'를 사용합니다.
MODEL_DIR = settings.MODEL_PATH


class ClassificationModule:
    def __init__(self):
        log.info(f"Initializing Classification module. Loading models from: {MODEL_DIR}")

        # 🔴 [핵심 3] NVIDIA GPU 감지 (Windows/Cloud)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        log.info(f"Classification module using device: {self.device}")

        # ocr_ver.2와 동일한 모델 파일 경로 정의 (기준 경로만 변경)
        vectorizer_path = os.path.join(MODEL_DIR, 'tfidf_vectorizer.joblib')
        label_encoder_path = os.path.join(MODEL_DIR, 'label_encoder.joblib')
        model_path = os.path.join(MODEL_DIR, 'model.pth')

        try:
            # (ocr_ver.2 로직과 동일)
            if not os.path.exists(vectorizer_path):
                log.error(f"Vectorizer file not found at {vectorizer_path}")
                raise FileNotFoundError
            self.vectorizer = joblib.load(vectorizer_path)

            if not os.path.exists(label_encoder_path):
                log.error(f"Label encoder file not found at {label_encoder_path}")
                raise FileNotFoundError
            self.label_encoder = joblib.load(label_encoder_path)

            self.tokenizer = AutoTokenizer.from_pretrained('google-bert/bert-base-uncased')

            if not os.path.exists(model_path):
                log.error(f"Model file not found at {model_path}")
                raise FileNotFoundError

            self.model = AutoModel.from_pretrained('google-bert/bert-base-uncased')
            self.classifier = torch.nn.Linear(1768, len(self.label_encoder.classes_))

            # 🔴 [핵심 4] 가중치 로드 시 map_location=self.device 추가 (GPU/CPU 호환)
            state_dict = torch.load(model_path, map_location=self.device)
            self.classifier.load_state_dict(state_dict)

            # 🔴 [핵심 5] 모델을 감지된 장치(NVIDIA GPU)로 이동
            self.model.to(self.device)
            self.classifier.to(self.device)

            self.classifier.eval()  # 평가 모드로 설정
            log.info("Classification models loaded successfully.")

        except Exception as e:
            log.error(f"Error loading classification models: {e}", exc_info=True)
            self.vectorizer = None
            self.label_encoder = None
            self.model = None
            self.classifier = None

    def predict(self, ocr_text: str) -> str:
        """
        OCR 텍스트를 기반으로 문서 유형을 분류합니다.
        (ocr_ver.2 원본 로직 + GPU 최적화)
        """
        if not all([self.vectorizer, self.label_encoder, self.model, self.classifier]):
            log.error("Classification module is not initialized. Returning 'other'.")
            return "other"

        if not ocr_text:
            log.warning("Empty OCR text received for classification. Returning 'other'.")
            return "other"

        try:
            # 1. TF-IDF 피처 생성 (CPU)
            tfidf_features = self.vectorizer.transform([ocr_text]).toarray()

            # 2. BERT 피처 생성 (GPU)
            inputs = self.tokenizer(ocr_text, return_tensors='pt', truncation=True, max_length=512, padding=True)

            # 🔴 [핵심 6] 모델 입력을 NVIDIA GPU로 이동
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
            bert_features = outputs.last_hidden_state[:, 0, :].cpu().numpy()

            # 3. 피처 결합 (CPU)
            combined_features = np.concatenate([tfidf_features, bert_features], axis=1)

            # 4. 분류 (GPU)
            # 🔴 [핵심 7] 결합된 피처를 다시 NVIDIA GPU로 이동
            combined_features_tensor = torch.tensor(combined_features, dtype=torch.float32).to(self.device)

            with torch.no_grad():
                logits = self.classifier(combined_features_tensor)
                predictions = torch.argmax(logits, dim=1)

            # 5. 레이블 반환 (CPU)
            predicted_label = self.label_encoder.inverse_transform(predictions.cpu().numpy())[0]
            log.info(f"Classification prediction: {predicted_label}")
            return predicted_label

        except Exception as e:
            log.error(f"Error during classification: {e}", exc_info=True)
            return "other"