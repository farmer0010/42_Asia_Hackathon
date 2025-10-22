from celery import Celery
import meilisearch
import uuid
from presidio_analyzer import AnalyzerEngine
import pytesseract
from PIL import Image
import io

# Celery 애플리케이션 생성
celery_app = Celery(
    "tasks",
    broker="redis://redis-broker:6379/0",
    backend="redis://redis-broker:6379/0"
)

# 클라이언트 및 엔진 초기화
client = meilisearch.Client(url="http://meilisearch:7700")
analyzer = AnalyzerEngine()


@celery_app.task
def process_document(filename: str, file_content: bytes):
    print(f"'{filename}' 문서에 대한 처리를 시작합니다...")

    extracted_text = ""
    try:
        # --- OCR 기능 추가 ---
        print("Tesseract OCR을 사용하여 텍스트를 추출합니다...")
        # 전달받은 파일 내용을 이미지로 변환
        image = Image.open(io.BytesIO(file_content))
        # Tesseract를 사용하여 영어 텍스트 추출
        extracted_text = pytesseract.image_to_string(image, lang='eng')
        print("OCR 텍스트 추출 완료.")
        # --------------------
    except Exception as e:
        print(f"OCR 처리 중 에러 발생: {e}")
        extracted_text = f"OCR failed for {filename}"

    # PII 탐지 (이제 가짜 텍스트 대신, OCR로 추출한 실제 텍스트를 사용)
    try:
        print(f"'{filename}'의 추출된 내용에서 PII를 탐지합니다...")
        pii_results = analyzer.analyze(text=extracted_text, language='en')
        if pii_results:
            print("개인정보가 탐지되었습니다:")
            for result in pii_results:
                print(f"- Type: {result.entity_type}, Text: {extracted_text[result.start:result.end]}")
        else:
            print("개인정보가 탐지되지 않았습니다.")
    except Exception as e:
        print(f"PII 탐지 중 에러 발생: {e}")

    # MeiliSearch 인덱싱
    try:
        print(f"'{filename}'의 메타데이터를 MeiliSearch에 인덱싱합니다...")
        index = client.index("documents")
        doc_id = str(uuid.uuid4())
        response = index.add_documents([
            # 이제 추출된 텍스트도 함께 저장합니다.
            {"id": doc_id, "filename": filename, "content": extracted_text}
        ])
        task_uid = response.get('uid') if isinstance(response, dict) else response
        print(f"MeiliSearch 인덱싱 작업이 제출되었습니다: {task_uid}")
    except Exception as e:
        print(f"MeiliSearch 인덱싱 중 에러 발생: {e}")

    result = f"'{filename}' 문서 처리가 완료되었습니다. 추출된 텍스트 길이: {len(extracted_text)}"
    print(result)
    return result