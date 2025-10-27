from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import json
import re
import pandas as pd
from pathlib import Path

class DataExtractor:
    def __init__(self, model_name='dslim/bert-base-NER'):
        """
        범용 NER 모델 로드
        """
        print("Loading NER model...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.model.eval()
        
        # labels.csv에서 읽을 추출 설정
        self.extraction_config = {}  # {doc_type: [field1, field2, ...]}
        
        print("NER model ready!")

    def configure_from_labels(self, labels_csv_path):
        """
        labels.csv를 읽어서 어떤 문서에서 뭘 추출할지 파악
        
        예: 
        filename,doc_type,vendor,amount,date
        inv1.pdf,invoice,CompanyA,1500.75,2025-01-01
        
        → extraction_config = {
            'invoice': ['vendor', 'amount', 'date']
        }
        """
        print("\nConfiguring extractor from labels.csv...")
        df = pd.read_csv(labels_csv_path)
        
        # 기본 컬럼 제외 (filename, doc_type)
        base_columns = ['filename', 'doc_type']
        
        for doc_type in df['doc_type'].unique():
            # 이 문서 타입의 추출 필드
            type_df = df[df['doc_type'] == doc_type]
            fields = [col for col in type_df.columns if col not in base_columns]
            
            # NaN이 아닌 필드만 (실제 값이 있는 필드)
            actual_fields = []
            for field in fields:
                if not type_df[field].isna().all():
                    actual_fields.append(field)
            
            if actual_fields:
                self.extraction_config[doc_type] = actual_fields
                print(f"  {doc_type}: {actual_fields}")
        
        print(f"Extraction configured for {len(self.extraction_config)} document types")

    def _run_ner(self, text):
        """
        BERT-NER로 모든 엔티티 추출
        """
        tokens = self.tokenizer(text, return_tensors='pt', 
                                truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = self.model(**tokens)
        
        predictions = torch.argmax(outputs.logits, dim=2)
        
        # 엔티티별 분류 (모델의 실제 레이블 사용)
        entities = {
            'PER': [],      # Person
            'ORG': [],      # Organization
            'LOC': [],      # Location
            'MISC': [],     # Miscellaneous
        }
        
        current_entity = []
        current_type = None
        
        for idx, pred in enumerate(predictions[0]):
            label = self.model.config.id2label[pred.item()]
            token = self.tokenizer.decode(tokens['input_ids'][0][idx]).strip()
            
            if token in ['[CLS]', '[SEP]', '[PAD]'] or not token:
                continue
            
            # B- (시작), I- (계속)
            if label.startswith('B-'):
                if current_entity and current_type:
                    entities[current_type].append(' '.join(current_entity))
                current_type = label[2:]  # B-PER → PER
                current_entity = [token]
            elif label.startswith('I-') and current_type:
                current_entity.append(token)
            else:
                if current_entity and current_type:
                    entities[current_type].append(' '.join(current_entity))
                current_entity = []
                current_type = None
        
        # 마지막 엔티티
        if current_entity and current_type:
            entities[current_type].append(' '.join(current_entity))
        
        return entities

    def extract(self, text, doc_type):
        """
        동적 필드 추출
        """
        # 이 문서 타입은 추출 안 함
        if doc_type not in self.extraction_config:
            return {}
        
        # NER 실행
        entities = self._run_ner(text)
        
        # 정규식으로 추가 패턴 추출
        patterns = self._extract_patterns(text)
        
        # 필드별 매칭
        result = {}
        for field in self.extraction_config[doc_type]:
            result[field] = self._match_field(field, entities, patterns, text)
        
        return result

    def _extract_patterns(self, text):
        """
        정규식으로 패턴 추출
        """
        patterns = {}
        
        # 날짜 패턴
        date_pattern = r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}'
        patterns['dates'] = re.findall(date_pattern, text)
        
        # 금액 패턴
        amount_pattern = r'[\$€£¥฿]\s*[\d,]+\.?\d*|\d+\.\d{2}'
        patterns['amounts'] = re.findall(amount_pattern, text)
        
        # 통화
        if '$' in text or 'USD' in text:
            patterns['currency'] = 'USD'
        elif '€' in text or 'EUR' in text:
            patterns['currency'] = 'EUR'
        elif '฿' in text or 'THB' in text:
            patterns['currency'] = 'THB'
        else:
            patterns['currency'] = None
        
        return patterns

    def _match_field(self, field_name, entities, patterns, text):
        """
        필드 이름을 보고 적절한 값 매칭
        """
        field_lower = field_name.lower()
        
        # Vendor, Company, Store → ORG
        if any(kw in field_lower for kw in ['vendor', 'company', 'store', 'supplier']):
            return entities['ORG'][0] if entities['ORG'] else None
        
        # Name, Person → PER
        elif any(kw in field_lower for kw in ['name', 'person', 'customer']):
            return entities['PER'][0] if entities['PER'] else None
        
        # Date, Invoice_date → DATE
        elif 'date' in field_lower:
            if patterns['dates']:
                return patterns['dates'][0]
            elif entities['DATE']:
                return entities['DATE'][0]
            return None
        
        # Amount, Total, Price → MONEY
        elif any(kw in field_lower for kw in ['amount', 'total', 'price', 'cost']):
            if patterns['amounts']:
                # 가장 큰 금액
                nums = [float(re.sub(r'[^\d.]', '', a)) for a in patterns['amounts']]
                return max(nums)
            return None
        
        # Currency → 통화
        elif 'currency' in field_lower:
            return patterns['currency']
        
        # Experience, Education 등 → 첫 CARDINAL 또는 텍스트 검색
        else:
            # 기본: 필드 이름 주변 텍스트 찾기 (간단한 휴리스틱)
            pattern = rf'{field_name}[:\s]+([^\n]+)'
            match = re.search(pattern, text, re.ignorecase)
            if match:
                return match.group(1).strip()
            return None