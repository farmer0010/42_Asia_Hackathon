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


class DocumentClassifier:
    def __init__(self, model_name='distilbert-base-uncased'):
        self.model_name = model_name
        self.tokenizer = DistilBertTokenizer.from_pretrained(model_name) #텍스트를 숫자로
        self.labels = ['invoice', 'receipt', 'resume', 'report', 'contract']
        self.label_to_id = {label: i for i, label in enumerate(self.labels)}
        self.id_to_label = {i: label for i, label in enumerate(self.labels)}
        self.model = None

    def train(self, labels_csv_path, ocr_results_path, output_dir='models/classifier'):
        print("Training Classification Model")
    
        # Step 1: 데이터 로드
        print("\nStep 1: Loading data...")
        df = pd.read_csv(labels_csv_path)
        
        with open(ocr_results_path, 'r', encoding='utf-8') as f:
            ocr_results = json.load(f)
        
        print(f"Loaded {len(df)} labels from CSV")
        print(f"Loaded {len(ocr_results)} OCR results")
        
        # Step 2: 학습 데이터 준비
        print("\nStep 2: Preparing training data...")
        texts = []
        labels = []
        skipped = 0
        
        for _, row in df.iterrows():
            filename = row['filename']
            doc_type = row['doc_type']
            
            if filename not in ocr_results:
                print(f"Warning: {filename} not found in OCR results, skipping...")
                skipped += 1
                continue

            # error 처리
            if 'error' in ocr_results[filename]:
                print(f"Warning: {filename} OCR error, skipping...")
                skipped += 1
                continue
            
            text = ocr_results[filename].get('full_text') or ocr_results[filename].get('text')
            texts.append(text)
            labels.append(self.label_to_id[doc_type])
        
        print(f"Prepared {len(texts)} training samples")
        if skipped > 0:
            print(f"Skipped {skipped} samples due to errors")
        
        # Step 3: Dataset 생성
        print("\nStep 3: Creating dataset...")
        dataset = Dataset.from_dict({
            'text': texts,
            'label': labels
        })
        
        print(f"Dataset created with {len(dataset)} samples")
        
        # Step 4: Tokenization
        print("\nStep 4: Tokenizing text...")
        
        def tokenize_function(examples):
            return self.tokenizer(
                examples['text'],
                padding='max_length',
                truncation=True,
                max_length=512
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        print("Tokenization complete!")
        
        # Step 5: 모델 초기화
        print("\nStep 5: Initializing model...")
        self.model = DistilBertForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=len(self.labels),
            id2label=self.id_to_label,
            label2id=self.label_to_id
        )
        print(f"Model initialized for {len(self.labels)} classes")
        
        # Step 6: 학습 설정
        print("\nStep 6: Configuring training...")
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=3,
            per_device_train_batch_size=8,
            learning_rate=2e-5,
            logging_steps=10,
            save_strategy='epoch',
            save_total_limit=2,
        )
        print("Training configuration set")
        
        # Step 7: 학습 실행
        print("\nStep 7: Starting training...")
        print("This may take 30-60 minutes...")
        
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset,
        )
        
        trainer.train()
        print("\nTraining complete!")
        
        # Step 8: 모델 저장
        print("\nStep 8: Saving model...")
        self.save_model(output_dir)
        print(f"Model saved to {output_dir}")
        
        print("\n" + "=" * 60)
        print("Training Complete!")
        print("=" * 60)
    
    def classify(self, text):
        if self.model is None:
            raise Exception("Error: Model not loded! Call load_model() first.")
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=512
        )
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
            print("Error: No model to save!")
            return
        print(f"Saving model to {path}...")
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
        print("Model saved!")

    def load_model(self, path):
        print(f"Loading model from {path}...")
        self.model = DistilBertForSequenceClassification.from_pretrained(path)
        self.tokenizer = DistilBertTokenizer.from_pretrained(path)
        print("Model loaded!")

# 이거 테스트하는거임
if __name__ == '__main__':
    print("=" * 60)
    print("Classification Module Test")
    print("=" * 60)
    
    # Test 1: 초기화
    print("\nTest 1: Initializing classifier...")
    classifier = DocumentClassifier()
    print(f"Labels: {classifier.labels}")
    print(f"label_to_id: {classifier.label_to_id}")
    print("Initialization successful!")
    
    # Test 2: 사전학습 모델 로드
    print("\nTest 2: Loading pretrained model...")
    classifier.model = DistilBertForSequenceClassification.from_pretrained(
        'distilbert-base-uncased',
        num_labels=5,
        id2label=classifier.id_to_label,
        label2id=classifier.label_to_id
    )
    print("Model loaded!")
    
    # Test 3: classify() 함수 테스트
    print("\nTest 3: Testing classify() function...")
    
    # 테스트용 텍스트들
    test_texts = {
        "sample1 (invoice)": "Commercial Invoice ABC Exports Total Amount Due 13000.00 Payment Method Wire Transfer",
        "sample2 (receipt)": "Receipt Supermarket Sub Total 107.60 Cash Change Thank You",
        "sample3 (invoice)": "Malaysia Invoice Balance Due 8480.00 Payment Instruction"
    }
    
    for name, text in test_texts.items():
        result = classifier.classify(text)
        print(f"{name}: {result['doc_type']} (confidence: {result['confidence']:.2%})")
    
        # Test 4: 메모리 사용량 체크
    print("\nTest 4: Memory usage...")
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {memory_mb:.2f} MB")
    
    print("\nAll tests passed!")