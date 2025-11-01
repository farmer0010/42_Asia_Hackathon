import os
import torch
from transformers import DistilBertForSequenceClassification, DistilBertTokenizer
from torch.nn.functional import softmax
import logging
from typing import Dict, Any

# Loguru 로거 설정 (worker.py와 동일한 로거 사용)
log = logging.getLogger("uvicorn")


class DocumentClassifier:
    """
    [진짜 모듈] DistilBERT 모델을 사용하여 문서 텍스트를 분류합니다.
    (원본: ocr/src/classification_module.py)

    [수정] "데모 모드" 로직 추가
    모델 파일이 없어도 (training_set이 없어도) 크래시나지 않고,
    파일명을 기반으로 임시 분류를 수행합니다.
    """

    def __init__(self, model_path: str = None):
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # [수정] ocr/llm 폴더 기준 5개 클래스
        self.label_map = {0: 'invoice', 1: 'receipt', 2: 'contract', 3: 'report', 4: 'resume'}
        self.is_model_loaded = False  # ◀◀◀ [데모 모드] 플래그

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str):
        """
        지정된 경로에서 훈련된 모델과 토크나이저를 로드합니다.
        [수정] 모델이 없어도 크래시 나지 않도록 try-except 추가
        """
        try:
            if not os.path.exists(model_path):
                log.warning(f"Model path not found: {model_path}")
                log.warning("!!! RUNNING IN 'DEMO MODE'. Classification will be based on filename. !!!")
                self.is_model_loaded = False
                return

            self.model = DistilBertForSequenceClassification.from_pretrained(model_path)
            self.tokenizer = DistilBertTokenizer.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()
            self.is_model_loaded = True  # ◀◀◀ [데모 모드] 성공 시 플래그 설정
            log.info(f"Successfully loaded REAL classifier model from {model_path}")

        except Exception as e:
            log.error(f"Failed to load model from {model_path}: {e}. Falling back to DEMO MODE.")
            self.is_model_loaded = False

    def classify(self, text: str, file_name: str = "unknown.txt") -> Dict[str, Any]:
        """
        주어진 텍스트를 분류합니다.
        [수정] 모델이 로드되지 않았으면 "데모 모드" 분류 수행
        """
        # ◀◀◀ [데모 모드] 로직 ◀◀◀
        if not self.is_model_loaded:
            log.warning(f"Classifying using DEMO logic (filename match for: {file_name}).")
            file_name_lower = file_name.lower()
            if "invoice" in file_name_lower:
                return {"doc_type": "invoice", "confidence": 1.0, "demo": True}
            elif "receipt" in file_name_lower:
                return {"doc_type": "receipt", "confidence": 1.0, "demo": True}
            elif "contract" in file_name_lower:
                return {"doc_type": "contract", "confidence": 1.0, "demo": True}
            elif "report" in file_name_lower:
                return {"doc_type": "report", "confidence": 1.0, "demo": True}
            elif "resume" in file_name_lower:
                return {"doc_type": "resume", "confidence": 1.0, "demo": True}
            else:
                return {"doc_type": "unknown", "confidence": 1.0, "demo": True}

        # ▼▼▼ [진짜 모드] 로직 ▼▼▼
        log.debug(f"Classifying using REAL model.")
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = softmax(logits, dim=1)
            confidence, predicted_class_idx = torch.max(probabilities, dim=1)

        predicted_label = self.label_map.get(predicted_class_idx.item(), "unknown")

        return {
            "doc_type": predicted_label,
            "confidence": confidence.item()
        }