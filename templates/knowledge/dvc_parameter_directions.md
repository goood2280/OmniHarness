# DVC Parameter Direction Rules (FabCanvas)

> 참조 문서. SPC 트렌드·ML 결과에 **개선 / 악화 / 타겟이탈** 방향 라벨을 붙일 때 orchestrator·dev-lead 가 읽고 적용한다.
> 원래 `dvc-curator` 에이전트가 소유하던 룰을 knowledge 로 이관.

## 방향성 카테고리

- `lower_is_better` — 낮을수록 성능 좋음
- `higher_is_better` — 높을수록 성능 좋음
- `target_centered` — 설계 타겟 중심, 양쪽으로 벗어나면 악화
- `context_dependent` — HW 조건에 따라 분기 (단일 "좋다/나쁘다" 결론 금지)

## 기본 파라미터 룰

| 파라미터 | 방향 | 의미 |
|---|---|---|
| Rc | lower_is_better | 접촉저항 |
| Rch | target_centered | 채널저항 설계값 기준 |
| ACint | lower_is_better | AC interconnect |
| AChw | context_dependent | HW 조건 분기 |
| DC Ioff | lower_is_better | 누설 |
| DC Ion | higher_is_better | 구동전류 |
| DC Vth | target_centered | 문턱전압 |
| lkg | lower_is_better | 누설전류 |

정식 소스: `data/dvc_rules.json` (파라미터 · 방향성 · 설계 타겟 · 해석 문구 템플릿)

## 해석 산출 절차

1. SPC 가 감지한 트렌드 방향 (상승/하강) + 방향성 룰 결합 → `{개선, 악화, 타겟이탈, 판단보류}`
2. `target_centered` 는 타겟 대비 ± 편차 범위·허용 폭을 반드시 명시
3. `context_dependent` 는 조건 분기 없이 단일 결론 내지 말 것
4. `causal_direction_matrix.md` 와 교차 — 방향성 변화의 원인 area 가 상류 area 인지 확인

## FabCanvas 내 적용 지점

- SPC 트렌드 위 **개선/악화 화살표 오버레이**
- ML 해석 패널 자동 주석
- 대시보드 KPI 카드 방향 배지
- 리포트 해석 문구 자동 생성

## 제약

- 사내 설계 타겟값/사내 스펙 리밋 직접 명시 금지. 사용자 프로파일 주입값 또는 학계 공개 수준만 사용.
- JSON 룰 테이블 + 템플릿 문자열 형태 유지.
