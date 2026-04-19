# Adapter Mapping Rules (FabCanvas)

> 참조 문서. S3 parquet 컬럼 매핑 / 타입 추론 / 역할 매핑 UI 작성 시 orchestrator·dev-lead 가 읽고 적용한다.
> 원래 `adapter-engineer` 에이전트가 소유하던 룰을 knowledge 로 이관.

## 프로파일 & 사전

- `data/adapter_profiles/<profile>.json` — 프로파일별 컬럼 alias, 시간 / wafer_id / 측정값 매핑
- `data/relation_hint_dict.json` — 3-tier relation hint 기본 사전 + 자동 캐스팅 규칙

## 타입 추론 휴리스틱

- **datetime**: ISO 문자열, epoch ms, pandas Timestamp
- **numeric**: int / float, 단위 접미사 처리
- **categorical**: low-cardinality, code 컬럼

## 3-tier relation hint 우선순위 (고정)

1. **exact** — 완전일치
2. **alias** — 사전 매핑 (예: `slot_id` / `wafer_no` / `wf_id` → `wafer_id`)
3. **substring** — 부분문자열 fallback

## 역할 매핑 UI 질문 템플릿

- 시간 컬럼은?
- wafer_id 는?
- 측정값 컬럼은?
- lot_id 는?

## 자동 캐스팅

- str ↔ int 캐스팅 필요 케이스 룰화 (예: wafer_id `"001"` vs `1` 불일치)

## FabCanvas 내 적용 지점

- 온보딩 위자드 (컬럼 매핑)
- 파일 브라우저 등록 플로우
- relation hint 매칭 엔진
- 프로파일 저장/재적용

## 교차 참조

- `process_area_rules.md` — 사내 step_id ↔ 표준 area 연결

## 제약

- 사내 실제 컬럼명·DataLake 경로·파일 규약 직접 명시 금지. 사용자 제공 샘플로만 alias 사전 구성.
- JSON 사전 + 규칙 함수 형태 유지. 우선순위는 `exact > alias > substring` 고정.
