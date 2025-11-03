# D:\42_asia-hackathon\42_Asia_Hackathon-backend\app\pipeline\classification_module.py
# (ocr_ver.2의 로직을 기반으로 경로 수정을 완료한 최종본)

import os
import joblib
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
import numpy as np

# 🔴 [핵심 수정 1] backend의 'settings'를 import하여 환경 변수를 읽습니다.
from app.config import settings
from ..logger_config import setup_logging

log = setup_logging()

# 🔴 [핵심 수정 2]
# 원본(ocr_ver.2)의 하드코딩된 로컬 경로 "./models/classifier" 대신,
# docker-compose.yml에서 주입된 'settings.MODEL_PATH'를 사용합니다.
# (이 경로는 컨테이너 내부의 '/usr/src/models/classifier'가 됩니다.)
MODEL_DIR = settings.MODEL_PATH


#

class ClassificationModule:
    def __init__(self):
        log.info(f"Initializing Classification module. Loading models from: {MODEL_DIR}")

        # 모델 파일 경로를 settings.MODEL_PATH 기준으로 정의
        vectorizer_path = os.path.join(MODEL_DIR, 'tfidf_vectorizer.joblib')
        label_encoder_path = os.path.join(MODEL_DIR, 'label_encoder.joblib')
        model_path = os.path.join(MODEL_DIR, 'model.pth')

        try:
            # TF-IDF Vectorizer 로드
            if not os.path.exists(vectorizer_path):
                log.error(f"Vectorizer file not found at {vectorizer_path}")
                raise FileNotFoundError
            self.vectorizer = joblib.load(vectorizer_path)

            # Label Encoder 로드
            if not os.path.exists(label_encoder_path):
                log.error(f"Label encoder file not found at {label_encoder_path}")
                raise FileNotFoundError
            self.label_encoder = joblib.load(label_encoder_path)

            # (Hugging Face) Tokenizer 로드 (이것은 인터넷에서 다운로드됩니다)
            self.tokenizer = AutoTokenizer.from_pretrained('google-bert/bert-base-uncased')

            # PyTorch 모델 로드 (가중치만)
            if not os.path.exists(model_path):
                log.error(f"Model file not found at {model_path}")
                raise FileNotFoundError

            # 모델 구조 정의 (BERT 기반)
            self.model = AutoModel.from_pretrained('google-bert/bert-base-uncased')
            # TF-IDF (1000) + BERT (768) = 1768 피처
            self.classifier = torch.nn.Linear(1768, len(self.label_encoder.classes_))

            # 저장된 가중치(state_dict) 로드
            # 🔴 [수정] GPU/CPU 호환성을 위해 map_location 추가
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(device)
            self.classifier.to(device)

            state_dict = torch.load(model_path, map_location=device)
            self.classifier.load_state_dict(state_dict)
            self.classifier.eval()  # 평가 모드로 설정

            log.info("Classification models loaded successfully.")
            log.info(f"Classifier classes: {self.label_encoder.classes_}")

        except FileNotFoundError:
            log.error(f"Critical model file not found in {MODEL_DIR}. Classification will fail.")
            # ... (오류 처리 부분은 원본과 동일) ...
            self.vectorizer = None
            self.label_encoder = None
            self.model = None
            self.classifier = None
        except Exception as e:
            log.error(f"Error loading classification models: {e}", exc_info=True)
            self.vectorizer = None
            self.label_encoder = None
            self.model = None
            self.classifier = None

    def predict(self, ocr_text: str) -> str:
        """
        OCR 텍스트를 기반으로 문서 유형을 분류합니다. (ocr_ver.2 원본 로직)
        """
        if not all([self.vectorizer, self.label_encoder, self.model, self.classifier]):
            log.error("Classification module is not initialized. Returning 'other'.")
            return "other"

        if not ocr_text:
            log.warning("Empty OCR text received for classification. Returning 'other'.")
            return "other"

        try:
            # 1. TF-IDF 피처 생성
            tfidf_features = self.vectorizer.transform([ocr_text]).toarray()

            # 2. BERT 피처 생성
            inputs = self.tokenizer(ocr_text, return_tensors='pt', truncation=True, max_length=512, padding=True)

            # 🔴 [수정] 모델 입력을 GPU/CPU 장치로 이동
            device = next(self.model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
            # [CLS] 토큰의 임베딩 사용
            bert_features = outputs.last_hidden_state[:, 0, :].cpu().numpy()

            # 3. 피처 결합 (원본 로직)
            combined_features = np.concatenate([tfidf_features, bert_features], axis=1)

            # 4. 분류
            combined_features_tensor = torch.tensor(combined_features, dtype=torch.float32).to(device)
            with torch.no_grad():
                logits = self.classifier(combined_features_tensor)
                predictions = torch.argmax(logits, dim=1)

            # 5. 레이블 반환
            predicted_label = self.label_encoder.inverse_transform(predictions.cpu().numpy())[0]
            log.info(f"Classification prediction: {predicted_label}")
            return predicted_label

        except Exception as e:
            log.error(f"Error during classification: {e}", exc_info=True)
            return "other"