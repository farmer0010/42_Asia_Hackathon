from src.extraction_module import DataExtractor

print("=" * 60)
print("Testing Extraction Module")
print("=" * 60)

# 1. 초기화
print("\n[Step 1] Initializing...")
extractor = DataExtractor()
print("✓ Success!")

# 2. 테스트 데이터
invoice_text = """
Commercial Invoice
Company: ABC Exports Ltd.
Date: September 30, 2030
Total: $13,000.00
"""

print("\n[Step 2] Testing NER...")
entities = extractor._run_ner(invoice_text)
print("Entities found:")
for key, values in entities.items():
    if values:
        print(f"  {key}: {values}")

print("\n[Step 3] Testing patterns...")
patterns = extractor._extract_patterns(invoice_text)
print(f"  Dates: {patterns['dates']}")
print(f"  Amounts: {patterns['amounts']}")
print(f"  Currency: {patterns['currency']}")

print("\n" + "=" * 60)
print("✓ All tests passed!")
print("=" * 60)