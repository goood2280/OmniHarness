# Process Area Tagging Rules (FabCanvas)

> 참조 문서. ML / SPC / 리포트 작성 시 orchestrator·dev-lead 가 읽고 적용한다.
> 원래 `process-tagger` 에이전트가 소유하던 룰을 **knowledge 로 이관** (에이전트 레이어 극장 제거).

## 표준 공정 영역 라벨

2nm GAA Nanosheet 일반 흐름 기준 8 area:

- **STI** (Shallow Trench Isolation)
- **Well / VT Implant**
- **PC** (Gate Patterning / Nanosheet release / dummy gate)
- **Gate** (HKMG)
- **Spacer**
- **S/D Epi**
- **MOL** (Contact, via-to-gate)
- **BEOL** (M1 ~ Mn metal layers)

## 매핑 소스

- `data/process_area_map.csv` — step_id · func_step · area 3-열 매핑 테이블
- 사내 step_id ↔ 표준 label 연결은 `adapter_mapping_rules.md` 와 공동 책임

## 태깅 원칙

1. func_step 명칭을 표준 area 라벨로 정규화한 뒤 태깅
2. ML feature 리스트 → feature 별 area 부여 → importance 를 area 단위로 합산
3. SPC 트렌드 차트에 area 색상 밴드 매핑 제공
4. 매핑 불가 feature → `unknown` 태그. 인과 판단은 `causal_direction_matrix.md` 로 위임 전에 보류 플래그.

## FabCanvas 내 적용 지점

- ML 대시보드: SHAP importance area 그룹핑
- SPC: 트렌드 색상 밴드
- 이상 탐지 리포트: 물리 해석 블록

## 제약

- 사내 실제 장비명·사내 고유 step_id 원본 노출 금지. 학계 공개 수준 명칭 (예: "HKMG Gate stack deposition") 으로만.
- LLM 추론 없이 동작하는 CSV/JSON 룰 테이블 형태 유지.
