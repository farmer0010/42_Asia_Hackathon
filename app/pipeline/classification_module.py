from transformers import (
    DistilBertForSequenceClassification,
    DistilBertTokenizer,
    Trainer,
    TrainingArguments,
)
from datasets import Dataset
import pandas as pd
import json
import torch
import logging

log = logging.getLogger(__name__)


class DocumentClassifier:
    def __init__(self, model_name='distilbert-base-uncased'):
        self.model_name = model_name
        self.tokenizer = DistilBertTokenizer.from_pretrained(model_name)  # 텍스트를 숫자로
        self.labels = ['invoice', 'receipt', 'resume', 'report', 'contract']  # 기본값
        self.label_to_id = {label: i for i, label in enumerate(self.labels)}
        self.id_to_label = {i: label for i, label in enumerate(self.labels)}
        self.model = None

    def train(self, labels_csv_path, ocr_results_path, output_dir='models/classifier'):
        log.info("Training Classification Model")

        # Step 1: 데이터 로드
        log.info("\nStep 1: Loading data...")
        df = pd.read_csv(labels_csv_path)

        # 해커톤 당일 긴급 수정 가이드 적용 (자동으로 doc_type 인식)
        self.labels = sorted(df['doc_type'].unique().tolist())
        self.label_to_id = {label: i for i, label in enumerate(self.labels)}
        self.id_to_label = {i: label for i, label in enumerate(self.labels)}
        log.info(f"Auto-detected document types: {self.labels}")

        with open(ocr_results_path, 'r', encoding='utf-8') as f:
            ocr_results = json.load(f)

        log.info(f"Loaded {len(df)} labels from CSV")
        log.info(f"Loaded {len(ocr_results)} OCR results")

        # Step 2: 학습 데이터 준비
        log.info("\nStep 2: Preparing training data...")
        texts = []
        labels = []
        skipped = 0

        for _, row in df.iterrows():
            filename = row['filename']
            doc_type = row['doc_type']

            if filename not in ocr_results:
                log.warning(f"Warning: {filename} not found in OCR results, skipping...")
                skipped += 1
                continue

            # error 처리
            if 'error' in ocr_results[filename]:
                log.warning(f"Warning: {filename} OCR error, skipping...")
                skipped += 1
                continue

            text = ocr_results[filename]['text']
            texts.append(text)
            labels.append(self.label_to_id[doc_type])

        log.info(f"Prepared {len(texts)} training samples")
        if skipped > 0:
            log.warning(f"Skipped {skipped} samples due to errors")

        # Step 3: Dataset 생성
        log.info("\nStep 3: Creating dataset...")
        dataset = Dataset.from_dict({
            'text': texts,
            'label': labels
        })

        log.info(f"Dataset created with {len(dataset)} samples")

        # Step 4: Tokenization
        log.info("\nStep 4: Tokenizing text...")

        def tokenize_function(examples):
            return self.tokenizer(
                examples['text'],
                padding='max_length',
                truncation=True,
                max_length=512
            )

        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        log.info("Tokenization complete!")

        # Step 5: 모델 초기화
        log.info("\nStep 5: Initializing model...")
        self.model = DistilBertForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=len(self.labels),
            id2label=self.id_to_label,
            label2id=self.label_to_id
        )
        log.info(f"Model initialized for {len(self.labels)} classes")

        # Step 6: 학습 설정
        log.info("\nStep 6: Configuring training...")
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=3,
            per_device_train_batch_size=8,
            learning_rate=2e-5,
            logging_steps=10,
            save_strategy='epoch',
            save_total_limit=2,
        )
        log.info("Training configuration set")

        # Step 7: 학습 실행
        log.info("\nStep 7: Starting training...")
        log.info("This may take 30-60 minutes...")

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset,
        )

        trainer.train()
        log.info("\nTraining complete!")

        # Step 8: 모델 저장
        log.info("\nStep 8: Saving model...")
        self.save_model(output_dir)
        log.info(f"Model saved to {output_dir}")

        log.info("\n" + "=" * 60)
        log.info("Training Complete!")
        log.info("=" * 60)

    def classify(self, text):
        if self.model is None:
            log.error("Error: Model not loaded! Call load_model() first.")
            raise Exception("Error: Model not loaded! Call load_model() first.")

        # CPU 또는 MPS(M1/M2 Mac) 또는 CUDA(Nvidia) 자동 감지
        device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        self.model.to(device)

        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=512
        ).to(device)  # 입력 텐서도 같은 장치로 이동

        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            predicted_class = torch.argmax(predictions, dim=-1).item()
            confidence = predictions[0][predicted_class].item()

        return {
            'doc_type': self.id_to_label[predicted_class],
            'confidence': confidence
        }

    def save_model(self, path):
        if self.model is None:
            log.error("Error: No model to save!")
            return
        log.info(f"Saving model to {path}...")
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        log.info("Model saved!")

    def load_model(self, path):
        log.info(f"Loading model from {path}...")
        try:
            self.model = DistilBertForSequenceClassification.from_pretrained(path)
            self.tokenizer = DistilBertTokenizer.from_pretrained(path)

            # 모델의 config에서 label 정보 업데이트 (중요)
            if self.model.config.id2label:
                self.id_to_label = {int(k): v for k, v in self.model.config.id2label.items()}
                self.label_to_id = self.model.config.label2id
                self.labels = list(self.model.config.label2id.keys())
            else:
                log.warning(f"Model config at {path} does not contain id2label mapping. Using defaults.")

            log.info("Model loaded successfully!")
            log.info(f"Model labels: {self.labels}")
        except Exception as e:
            log.error(f"Failed to load model from {path}. Error: {e}", exc_info=True)
            raise