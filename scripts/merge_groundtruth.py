#!/usr/bin/env python3
"""
Groundtruth JSON 파일 병합 스크립트

config/ 폴더의 여러 groundtruth JSON 파일들을 하나로 병합합니다.
각 파일은 특정 문서 타입의 정답 데이터를 포함하고 있습니다.
"""

import json
from pathlib import Path
import sys

def merge_groundtruth_files(config_dir='config', output_file='config/groundtruth_merged.json'):
    """
    여러 groundtruth JSON 파일을 하나로 병합
    
    Args:
        config_dir: config 파일들이 있는 디렉토리
        output_file: 병합된 결과를 저장할 파일
    """
    print("="*60)
    print("Groundtruth JSON 파일 병합")
    print("="*60)
    
    config_path = Path(config_dir)
    
    # groundtruth*.json 파일들 찾기
    groundtruth_files = sorted(config_path.glob('groundtruth*.json'))
    groundtruth_files = [f for f in groundtruth_files if 'merged' not in f.name]
    
    if not groundtruth_files:
        print(f"❌ Error: {config_dir}/ 에서 groundtruth*.json 파일을 찾을 수 없습니다.")
        return False
    
    print(f"\n발견된 파일: {len(groundtruth_files)}개")
    for f in groundtruth_files:
        print(f"  - {f.name}")
    
    # 모든 파일 병합
    merged_data = {}
    stats = {}
    
    print("\n병합 시작...")
    for json_file in groundtruth_files:
        print(f"\n처리 중: {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 파일명에서 문서 타입 추출
            # invoice_*.pdf -> invoice
            # passport_*.png -> passport
            # resume_*.pdf -> resume
            # PO_*.pdf -> purchase_order
            # Customs_Form_*.pdf -> custom_form
            doc_types_found = set()
            for filename in data.keys():
                if filename.startswith('invoice_'):
                    doc_type = 'invoice'
                elif filename.startswith('passport_'):
                    doc_type = 'passport'
                elif filename.startswith('resume_'):
                    doc_type = 'resume'
                elif filename.startswith('PO_'):
                    doc_type = 'purchase_order'
                elif filename.startswith('Customs_Form_'):
                    doc_type = 'custom_form'
                else:
                    # 파일명에서 추론
                    doc_type = 'unknown'
                
                doc_types_found.add(doc_type)
            
            # 데이터 병합
            for filename, content in data.items():
                if filename in merged_data:
                    print(f"  ⚠️  Warning: {filename}이 이미 존재합니다. 덮어씁니다.")
                merged_data[filename] = content
            
            # 통계 수집
            stats[json_file.name] = {
                'count': len(data),
                'doc_types': sorted(doc_types_found)
            }
            
            print(f"  ✓ {len(data)}개 항목 로드됨")
            print(f"  ✓ 문서 타입: {', '.join(sorted(doc_types_found))}")
            
        except Exception as e:
            print(f"  ❌ Error: {json_file.name} 로드 실패 - {e}")
            return False
    
    # 결과 저장
    print(f"\n병합 완료! 총 {len(merged_data)}개 항목")
    print(f"\n저장 중: {output_file}")
    
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 저장 완료!")
    
    # 최종 통계
    print("\n" + "="*60)
    print("병합 통계")
    print("="*60)
    for filename, stat in stats.items():
        print(f"\n{filename}:")
        print(f"  항목 수: {stat['count']}")
        print(f"  문서 타입: {', '.join(stat['doc_types'])}")
    
    print(f"\n총 항목 수: {len(merged_data)}")
    print(f"출력 파일: {output_file}")
    
    # 문서 타입별 통계
    print("\n문서 타입별 통계:")
    type_counts = {}
    for filename in merged_data.keys():
        if filename.startswith('invoice_'):
            doc_type = 'invoice'
        elif filename.startswith('passport_'):
            doc_type = 'passport'
        elif filename.startswith('resume_'):
            doc_type = 'resume'
        elif filename.startswith('PO_'):
            doc_type = 'purchase_order'
        elif filename.startswith('Customs_Form_'):
            doc_type = 'custom_form'
        else:
            doc_type = 'unknown'
        
        type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
    
    for doc_type, count in sorted(type_counts.items()):
        print(f"  {doc_type}: {count}개")
    
    print("\n✅ 병합 완료!")
    return True

if __name__ == '__main__':
    # 명령줄 인자 처리
    if len(sys.argv) > 1:
        config_dir = sys.argv[1]
    else:
        config_dir = 'config'
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = 'config/groundtruth_merged.json'
    
    success = merge_groundtruth_files(config_dir, output_file)
    
    if not success:
        sys.exit(1)

