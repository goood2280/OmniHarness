# Causal Direction Matrix (FabCanvas)

> 참조 문서. ML 상관 결과에 **인과 신뢰도 등급** (높음 / 중간 / 낮음 / 의심) 을 부여할 때 orchestrator·dev-lead 가 읽고 적용한다.
> 원래 `causal-analyst` 에이전트가 소유하던 룰을 knowledge 로 이관.

## 기본 원칙

- 앞 공정 → 뒤 공정 영향: **강함**
- 뒤 공정 → 앞 공정 영향: **거의 없음** (= 기본 `의심` 플래그)
- 예외 — 형상 전사 케이스 (뒤 공정에서 앞 공정 형상이 재전사) → `중간` 으로 완화

## 매핑 소스

- `data/causal_matrix.csv` — area × area 인과 강도 매트릭스
  - 예: `Gate → Spacer 강함` · `BEOL → PC 거의없음` · `Gate → BEOL M1 중간 (전사)` · `S/D Epi → MOL 강함`
- `data/causal_exceptions.md` — 형상 전사 예외 규칙 누적 문서

## 판정 절차

1. 상관 페어 (source_feature, target_metric) → `process_area_rules.md` 기준으로 area 태깅
2. `causal_matrix.csv` 에서 `(area_src → area_tgt)` 조회
3. 역방향이면 `causal_exceptions.md` 의 전사 예외에 해당하는지 확인
4. 최종 등급: **높음 / 중간 / 낮음 / 의심**
5. `dvc_parameter_directions.md` 의 방향성과 교차 검증 — 예: `Rc` 상승 원인이 MOL·S/D Epi 쪽과 일치하는지

## FabCanvas 내 적용 지점

- ML 결과 패널의 **인과 신뢰도 배지**
- 이상 탐지 알림의 **통계적 vs 인과** 라벨
- 리포트 모드의 해석 가이드 블록

## 제약

- 사내 실제 장비·레시피·사내 결함 메커니즘 직접 명시 금지. 학계 공개 수준 메커니즘만.
- 룰 테이블과 예외 규칙은 항상 명시적 패턴으로 기록 (LLM 추론 의존 금지).
