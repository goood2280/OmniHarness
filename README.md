# OmniHarness

> 비주얼 오케스트레이션 레이어 — Claude Code 를 **에이전트 팀** 으로 운용하고 그 작업을 실시간으로 본다.

OmniHarness 는 도메인 전문가(코드를 직접 치지 않는 기획자/운영자/현장 엔지니어) 가 Claude Code 를 **자기 프로젝트의 전담 팀** 처럼 쓰도록 해준다. 회사명 · 업종 · 철학 · 목표를 한 번 세팅하면:

1. 오케스트레이터가 그 프로젝트에 가장 효율적인 에이전트 팀 구성을 제안한다
2. 사용자가 확인하면 **사무실 오피스 플로어 플랜** 이 그려진다 — 각 에이전트가 자기 책상에 앉아 있다
3. Claude Code 가 돌면서 담당 에이전트의 모니터가 켜지고 실시간 로그가 쌓인다
4. 모호한 결정을 만나면 **경영지원팀 리드(mgmt-lead)** 가 기술 원문을 사용자 언어로 풀어주고, 사용자 답변을 다시 에이전트가 바로 실행 가능한 구조로 변환한다 (양방향 번역)
5. 지식이 축적되면 에이전트들이 새 팀원 / 기능 / 리팩터링을 **자가진화 제안** 으로 올린다

---

## 두 가지 모드

### 🏢 커스텀 프로젝트 (Custom)
실전 개발·운영용. 프로젝트마다:
- 전용 사훈 · 팀 구성 · 지식 베이스
- 사무실 플로어 플랜에 팀별 방(Room) + 책상(Desk) + 모니터
- 탕비실(Canteen) 에는 이 프로젝트가 쓰는 MCP·스킬

복수 프로젝트를 관리할 수 있고, HUD 의 "⇆ 프로젝트 전환" 으로 빠르게 옮겨 다닌다.

### 🧭 제너럴 뷰어 (General)
탐색·학습용. 프로젝트 팀 세팅 없이 현재 폴더에서 Claude Code 가 내부적으로 **어떤 서브에이전트 · 툴 · 스킬** 을 쓰는지 원형 트리로 시각화한다. 기본은 메인 Claude 1개가 모든 툴 호출을 직접 수행, Task/Agent 툴을 쓰거나 로컬 `.claude/agents/` 가 있을 때만 가지가 자란다.

---

## 기본 팀 구조 (모든 프로젝트 공통)

| Tier | Role | Model | 역할 |
|---|---|---|---|
| 1 | `orchestrator` | opus | 총괄. 사용자 요청 분류 + 리드 위임 + HR 결정권자 |
| 2 | `dev-lead` | opus | 개발 리드. 기능 담당 에이전트 조율 |
| 2 | `mgmt-lead` | opus | 경영지원 리드. 사용자↔에이전트 **양방향 번역** |
| 2 | `eval-lead` | opus | 평가 리드. UX/검증/보안/도메인 리서치 파이프라인 |
| 3 | `reporter` · `hr` | sonnet | 경영지원 (요약 보고 + 조직 건전성) |
| 3 | 6명 평가팀 | sonnet | ux-reviewer · dev-verifier · user/admin-role-tester · security-auditor · domain-researcher |

프로젝트를 만들 때 오케스트레이터가 업종에 맞는 **개발팀 (dev-*)** 과 **도메인 전문가** 를 추가 제안한다. 사용자는 추가/제거 후 확정.

---

## 양방향 Q&A 번역

에이전트가 모호한 결정에 부딪힐 때:

```
에이전트가 기술 원문 올림 (pending_translation)
  ↓
mgmt-lead 가 사용자 언어로 풀어씀 (pending_user)
  ↓
사용자가 UI 에서 자유롭게 답변 (pending_answer_translation)
  ↓
mgmt-lead 가 에이전트용 구조화된 지시로 변환 (answered)
  ↓
에이전트가 즉시 실행 가능한 지시를 받아 작업 재개
```

사용자는 기술 용어를 몰라도, 에이전트는 모호한 지시를 받지 않는다.

---

## 자가진화

- **지식 축적**: 모든 에이전트가 `POST /api/knowledge` 로 배운 것을 기록 (주제 + 인사이트)
- **제안**: 오케스트레이터/HR 이 `POST /api/evolution` 으로 다음을 올릴 수 있다
  - `new_agent` — 새 담당자가 필요
  - `feature` — 프로젝트에 추가할 기능
  - `refactor` — 구조 개선
  - `retire_agent` — 활성도가 낮은 에이전트 정리
- 사용자는 UI 의 🌱 자가진화 탭에서 수락/거절만 결정

---

## 환경 변수 (.env)

모든 키는 워크스페이스 루트의 `.env` 에 둡니다. `.env.example` 를 복사해서 채워넣으세요.

```
cp .env.example .env
# 필요한 키만 채워넣으면 됨
```

- `GEMINI_API_KEY` — 캐릭터/아이템 이미지 생성용 (Nano Banana / Gemini 2.5 Flash Image)
- `ANTHROPIC_API_KEY` **또는** `CLAUDE_CODE_USE_BEDROCK=1 + AWS_*` — 💬 웹 채팅 orchestrator 용
- `OMNIHARNESS_URL` — CLI 훅이 POST 할 주소 (기본 http://localhost:8082)

백엔드와 `scripts/generate_assets.py` 둘 다 이 `.env` 를 자동 로드합니다.

## 아트 에셋 생성 (Gemini)

게임처럼 자유 배치 가능한 아트를 Nano Banana 로 뽑아 타일 폴더에 떨굽니다. 제너럴 뷰어 먼저 적용되고, 나중에 OfficeScene 으로 확장됩니다.

```bash
pip install google-genai
# .env 에 GEMINI_API_KEY 먼저 설정
python OmniHarness/scripts/generate_assets.py
```

생성되는 것:
- **캐릭터 스프라이트 시트** — `/public/tiles/chars/<agent>-sheet.png`. 한 파일에 5 포즈 (idle · Sonnet 평상 작업 · Opus 열일모드 · 손 든 질문 · 대기) 가 가로로 나열
- **아이템 타일** — `/public/tiles/items/<id>.png`. 책상 · 의자 · 화분 · 정수기 · 커피머신 · 서버랙 · 스킬북 등 자유 배치용
- **제너럴 뷰어 배경** — `/public/tiles/general/backdrop.png` (선택)

생성 후 자동으로 **일관성 평가 패스** 가 돌아요 — Gemini 비전이 생성된 시트들을 한꺼번에 보고 스타일 불일치 (픽셀 밀도 · 선 굵기 · 팔레트 · 포즈 배열) 를 찾아내 해당 시트를 재생성합니다. `--retry N` 으로 반복 횟수 조정, `--no-eval` 로 끄기 가능.

개별 옵션:
```bash
python OmniHarness/scripts/generate_assets.py --agent orchestrator   # 한 캐릭터만
python OmniHarness/scripts/generate_assets.py --item plant-snake     # 한 아이템만
python OmniHarness/scripts/generate_assets.py --backdrop             # 배경도 생성
python OmniHarness/scripts/generate_assets.py --force                # 이미 있어도 재생성
```

PNG 가 없는 에이전트는 자동으로 기존 SVG 프로시저럴 캐릭터로 폴백되기 때문에, 순차적으로 키가 없어도 동작합니다.

## Quick start

```bash
# 1) Backend
cd OmniHarness/backend
pip install "fastapi[standard]" uvicorn pydantic
uvicorn app:app --host 0.0.0.0 --port 8081

# 2) Frontend
cd OmniHarness/frontend
npm install
npm run build           # 또는 `npm run dev`

# 3) 열기
open http://localhost:8081
```

첫 방문에서는 **제너럴 vs 커스텀** 선택 → 커스텀이면 프로젝트 리스트 → 신규/기존 선택 → 팀 확정.

## 소비 프로젝트에 연결

```bash
# 소비 프로젝트(예: MyApp) 에서 에이전트 템플릿을 미러링
python ../OmniHarness/scripts/sync_to.py .

# 그 다음 `.claude/settings.json` 에 훅을 설정해 OmniHarness(:8081) 로
# 모든 Agent / Edit / Write / Bash 이벤트를 POST 하게 만든다.
```

이제 소비 프로젝트에서 `claude` 를 돌리면 뷰어에 실시간 상태가 찍힌다.

---

## 레이아웃

```
OmniHarness/
├── backend/
│   └── app.py                         # FastAPI — topology / questions /
│                                      # evolution / knowledge / projects / mode
├── frontend/src/
│   ├── App.jsx                        # 상태머신: mode → project → wizard → office
│   ├── ModeSelect.jsx                 # 첫 방문 모드 선택
│   ├── ProjectList.jsx                # 커스텀 모드 — 프로젝트 목록/생성
│   ├── Onboarding.jsx                 # 사훈 → 팀 제안 → 확정 (3단계 위저드)
│   ├── OfficeScene.jsx                # 커스텀 모드 — 사무실 플로어 플랜
│   ├── GeneralViewer.jsx              # 제너럴 모드 — 원형 트리
│   ├── Character.jsx                  # Zoo-style 동물 캐릭터 (SVG, PNG 덮어쓰기 가능)
│   ├── HUD.jsx                        # 모드 토글 · 에이전트/비용 · 가이드 · KO/EN
│   ├── MissionBanner.jsx              # 활성 프로젝트의 사훈 표시
│   ├── TabPanel.jsx
│   │   ├── Questions.jsx              # mgmt-lead 양방향 번역
│   │   ├── Evolution.jsx              # 자가진화 제안 · 누적 지식
│   │   ├── ActivityLog.jsx · Reports.jsx · Backlog.jsx · RequirementInput.jsx · OrgChart.jsx
│   ├── AgentPanel.jsx                 # 캐릭터 클릭 시 사이드 패널
│   └── McpPanel.jsx                   # 탕비실 아이템 상세
├── templates/
│   ├── agents/                        # 에이전트 템플릿 — 프로젝트 무관 제네릭
│   └── proposals/                     # HR 제안 저장소
├── projects/                          # 프로젝트별 mission.json + knowledge.json
└── scripts/
    ├── sync_to.py                     # 템플릿 → <소비 프로젝트>/.claude/agents/
    └── hook_to_omniharness.py         # stdin→viewer 브릿지
```

## 에셋

- **캐릭터**: `Character.jsx` 가 SVG 로 렌더 (Zoo-style: 여우·부엉이·곰·고양이·팬더·토끼·늑대·너구리·사슴·개구리 정장/후드 차림). 고해상도 PNG (`/tiles/chars/<agent-name>.png`) 를 드랍하면 해당 에이전트만 PNG 로 대체된다.
- **오피스 타일 (legacy)**: `public/tiles/` 에 LimeZu Modern Office · Interiors (Legacy characters) 의 일부 에셋을 참고용으로 보관.

## 비전

1. **Phase 1 (현재)**: 비주얼 + 오케스트레이션 레이어
2. **Phase 2**: SaaS · PyPI 패키지 · 설치형 배포. 타깃은 **코드를 직접 치지 않는 도메인 전문가** (반도체 공정 엔지니어, 이커머스 기획자, 데이터 분석가 등). UI 는 사용자가 친근한 사훈 배너 + Q&A 번역 루프 중심.

Anthropic 과 관련 없음.
