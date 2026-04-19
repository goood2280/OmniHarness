# OmniHarness

> **비주얼 오케스트레이션 레이어** — Claude Code 를 **팀** 으로 운용하고, 그 작업을 실시간으로 본다.
> **Visual orchestration layer** — run Claude Code as a **team** and watch them work in real time.

<p align="center">
  <sub>📸 <code>(오피스 플로어 플랜 캡처 / office floor-plan screenshot)</code></sub>
</p>

<p align="center">
  <sub>🎬 <code>(30초 데모 영상 / 30-second demo video)</code></sub>
</p>

---

🌐 **언어 / Language** — 원하는 섹션을 펼쳐 보세요. / Expand the section you want.

<details>
<summary><b>🇰🇷 한국어</b></summary>

<br>

OmniHarness 는 **코드를 직접 치지 않는 도메인 전문가** (기획자 · 운영자 · 현장 엔지니어) 가 Claude Code 를 **자기 프로젝트의 전담 팀** 처럼 쓰게 해줍니다. 회사명 · 업종 · 철학 · 목표를 한 번 세팅하면:

1. **오케스트레이터 (LLM)** 가 그 프로젝트에 진짜로 필요한 **에이전트 팀을 설계** 합니다 — 키워드 매칭이 아니라 실제 추론.
2. 사용자가 확인하면 **사무실 플로어 플랜** 이 그려집니다 — 각 에이전트가 자기 책상에 앉아 있습니다.
3. Claude Code 가 돌면서 담당 에이전트의 모니터가 켜지고 실시간 로그가 쌓입니다.
4. 모호한 결정을 만나면 **경영지원 리드 (mgmt-lead)** 가 기술 원문을 사용자 언어로 풀어주고, 사용자 답변을 다시 에이전트가 실행 가능한 구조로 변환합니다 (양방향 번역).
5. 지식이 축적되면 **감사원 (auditor)** 이 새 에이전트 · 기능 · 리팩터링을 **감사 제안** 으로 올립니다. 수락하면 실제 팀 로스터가 변경됩니다.

> 📸 <img width="80" height="600" alt="CaptureEdit_20260419145629" src="https://github.com/user-attachments/assets/14364a75-6f43-42d1-9deb-8fc035174cb1" />
 · 📸 `(Q&A 번역 화면 캡처)` · 🎬 `(감사 제안 영상)`

---

### 🚀 첫 방문 경험

첫 실행 시 튜토리얼이 뜹니다:
1. **언어 선택** — 🇰🇷 / 🇺🇸 두 버튼. 고른 언어로 이후 UI 가 전체 전환됩니다.
2. **환영** — 오피스 컨셉 짧은 소개.
3. **탭 투어** — 8개 탭 (조직도 · 활동 · 질문 · 요구사항 · 백로그 · 감사 · 누적 지식 · 보고서) 을 10초씩 설명.

이후엔 프로젝트 리스트로 바로 들어가서, 기존 프로젝트 선택 또는 신규 생성만 하면 됩니다.

---

### 🧠 핵심: LLM-기반 팀 설계

기존 "키워드 휴리스틱" 은 제거했습니다. API 키가 있으면:

- `ANTHROPIC_API_KEY` 또는 `CLAUDE_CODE_USE_BEDROCK=1 + AWS_*` → 오케스트레이터가 실제로 추론해서 **프로젝트 맞춤 팀** 을 제안합니다.
- 제안된 에이전트는 카탈로그에 없어도 됩니다 — LLM 이 새로 설계한 `dev-<이름>` / `<도메인-이름>` 이 mission.json 에 인라인으로 저장되어 토폴로지에 렌더됩니다.
- API 가 없으면 온보딩 위저드에 ⚠️ 경고가 뜨고, 키워드 폴백으로 동작합니다.

**판단 근거** 도 위저드에 같이 표시 — "이 프로젝트엔 왜 이 팀인지" 를 LLM 이 한 줄로 설명해줍니다.

> 📸 `(LLM 팀 제안 화면 캡처)`

---

### 👥 기본 팀 (모든 프로젝트 공통)

| Tier | Role | Model | 역할 |
|---|---|---|---|
| 1 | `orchestrator` | opus | 총괄 · 사용자 요청 분류 · 리드 위임 · HR 결정권자 |
| 2 | `dev-lead` | opus | 개발 리드. 기능 담당 에이전트 조율 |
| 2 | `mgmt-lead` | opus | 경영지원 리드. 사용자 ↔ 에이전트 **양방향 번역** |
| 2 | `eval-lead` | opus | 평가 리드. UX · 검증 · 보안 · 도메인 리서치 파이프라인 |
| 3 | `reporter` · `hr` · `auditor` | sonnet | 경영지원 (요약 보고 · 조직 건전성 · 감사) |
| 3 | 6명 평가팀 | sonnet | ux-reviewer · dev-verifier · user/admin-role-tester · security-auditor · domain-researcher |

프로젝트 생성 시 오케스트레이터가 이 기본 팀 **위에** dev-\* / 도메인 전문가를 추가 제안합니다.

---

### 🔄 양방향 Q&A 번역

```
에이전트가 기술 원문 올림             (pending_translation)
  ↓
mgmt-lead 가 사용자 언어로 풀어씀      (pending_user)
  ↓
사용자가 UI 에서 자유롭게 답변         (pending_answer_translation)
  ↓
mgmt-lead 가 에이전트용 구조화 지시로 변환 (answered)
  ↓
에이전트가 즉시 실행 가능한 지시를 받아 작업 재개
```

사용자는 기술 용어를 몰라도 되고, 에이전트는 모호한 지시를 받지 않습니다.

---

### 🔍 감사 · 조직 변경

"자가진화" 가 아닙니다. **감사원** 이라는 회사 역할이 주기적으로 조직을 점검합니다.

- **지식 축적**: 모든 에이전트가 `POST /api/knowledge` 로 배운 것을 기록.
- **감사 제안**: 감사원이 `POST /api/evolution` 로 새 에이전트 / 기능 / 리팩터 / 정리 제안을 올립니다.
- **수락 시 실제 반영**: `new_agent` · `retire_agent` 를 수락하면 `mission.json` 의 roster 가 실제로 변경되고 오피스 씬에 즉시 반영됩니다 (advisory-only 아님).

**권한 모델**: 에이전트 설정 `.md` 파일 수정은 오케스트레이터만 가능합니다. 인사팀 (hr) 은 추가 · 정리 *제안* 만 할 수 있고, 오케스트레이터 + 해당 팀 리드의 만장일치 승인이 필요합니다. 의견이 갈리면 오케스트레이터가 최종 결정합니다.

> 📸 `(감사 탭 캡처)`

---

### 🏢 오피스 씬

커스텀 모드의 메인 화면:

- **멀티밴드 벽/바닥 그라디언트** — 팀 룸이 에이전트 row 수만큼 wall+floor 밴드를 반복. 새 에이전트가 추가돼 row 가 늘어도 자동 재계산.
- **안정된 정렬** — "리드 먼저 → 이름 알파벳" 순. 에이전트 추가 / 정리되어도 기존 멤버가 흔들리지 않습니다.
- **스프라이트 정규화** — 각 캐릭터 셀을 크기 · 중앙 · 바닥앵커 기준으로 자동 정규화. 흰 배경 스트립은 `_chroma_key` 에 영구 포함.
- **우측 사이드바** — 캐릭터 / MCP / 스킬 클릭 시 동일한 우측 사이드 패널로 뜹니다. 열리면 메인이 왼쪽으로 밀려서 겹치지 않습니다.
- **좌측 TODO 패널** — ⚡작업중 · 📋예정 · ✅완료. 클릭하면 해당 작업 리스트 + 경영지원 리드가 쉬운 말로 풀어준 설명이 같이 뜹니다.

> 📸 `(스프라이트 시트 예시)` · 📸 `(TODO 패널 확장)`

---

### ⚙️ 환경 변수 (.env)

워크스페이스 루트의 `.env` 에 둡니다. `.env.example` 복사해서 채우세요.

```bash
cp .env.example .env
```

- `ANTHROPIC_API_KEY` **또는** `CLAUDE_CODE_USE_BEDROCK=1 + AWS_*` — LLM 팀 제안 + 💬 웹 채팅 orchestrator 에 필요
- `GEMINI_API_KEY` — 캐릭터 · 아이템 이미지 생성용 (Nano Banana / Gemini 2.5 Flash Image)
- `OMNIHARNESS_URL` — CLI 훅이 POST 할 주소 (기본 `http://localhost:8082`)

---

### 🎨 아트 에셋 생성 (Gemini)

```bash
pip install google-genai
python OmniHarness/scripts/generate_assets.py
```

생성:
- **캐릭터 스프라이트 시트** — `/public/tiles/chars/<agent>-sheet.png` (4x4 포즈 그리드)
- **아이템 타일** — `/public/tiles/items/<id>.png` (책상 · 의자 · 화분 · 정수기 · 커피머신 · 서버랙 · 스킬북)
- **배경** — `/public/tiles/general/backdrop.png` (선택)

생성 후 자동 **일관성 평가 패스** — Gemini 비전이 시트들을 한꺼번에 보고 스타일 불일치 (픽셀 밀도 · 선 굵기 · 팔레트) 를 잡아내 재생성. 크로마키 스테이지에 흰 배경 스트립 단계도 영구 포함되어 있어요.

---

### ⚡ Quick start

```bash
# 1) 백엔드
cd OmniHarness/backend
pip install "fastapi[standard]" uvicorn pydantic
uvicorn app:app --host 0.0.0.0 --port 8081

# 2) 프론트엔드
cd OmniHarness/frontend
npm install
npm run build

# 3) 열기
open http://localhost:8081
```

첫 방문: 튜토리얼 → 언어 선택 → 프로젝트 리스트 → 신규 / 기존 → 팀 확정.

---

### 🔌 소비 프로젝트에 연결

```bash
# 소비 프로젝트에서 에이전트 템플릿 미러링
python ../OmniHarness/scripts/sync_to.py .

# .claude/settings.json 에 훅 설정 → 모든 Agent · Edit · Write · Bash 이벤트를
# OmniHarness(:8081) 로 POST
```

이제 소비 프로젝트에서 `claude` 를 돌리면 뷰어에 실시간 상태가 찍힙니다.

---

### 🗂️ 레이아웃

```
OmniHarness/
├── backend/
│   └── app.py                         # FastAPI — topology · questions ·
│                                      # evolution · knowledge · projects ·
│                                      # LLM team proposal · mission
├── frontend/src/
│   ├── App.jsx                        # 상태머신: project → wizard → office
│   ├── ProjectList.jsx                # 프로젝트 목록 / 생성 (+ 언어 선택)
│   ├── Onboarding.jsx                 # 사훈 → LLM 팀 제안 → 확정 (3단계)
│   ├── OfficeScene.jsx                # 사무실 플로어 플랜 + 좌측 TODO 패널
│   ├── Tutorial.jsx                   # 첫 방문 튜토리얼 (언어 선택 + 탭 투어)
│   ├── HUD.jsx                        # 비용 · 가이드 · KO/EN
│   ├── Character.jsx · Sprite.jsx     # 캐릭터 렌더
│   ├── AgentPanel.jsx                 # 캐릭터 사이드패널 (설정 md 뷰 + 권한 안내)
│   ├── McpPanel.jsx                   # MCP/스킬 사이드패널 (동일 폼)
│   ├── TabPanel.jsx · Questions.jsx · Evolution.jsx · ...
│   └── i18n.js                        # KO/EN 번역 테이블 (default = EN)
├── templates/
│   ├── agents/                        # 에이전트 템플릿 (프로젝트 무관)
│   └── proposals/                     # 감사 제안 저장소
├── projects/                          # 프로젝트별 mission.json (커스텀 specs 포함)
└── scripts/
    ├── sync_to.py                     # 템플릿 → <소비 프로젝트>/.claude/agents/
    ├── hook_to_omniharness.py         # stdin → viewer 브릿지
    └── generate_assets.py             # Gemini 아트 생성 + 크로마키 + 흰배경 스트립
```

---

### 🖼️ 에셋

- **캐릭터 스프라이트** — SVG 기본, 고해상도 PNG 시트를 `/tiles/chars/<agent>-sheet.png` 에 드랍하면 해당 에이전트만 PNG 로 대체. 크기 · 중앙 · 바닥 앵커 자동 정규화.
- **아이템 타일** — 책상 · 의자 · 화분 · MCP 가전 · 스킬북 자유 배치.
- **전 에셋** — Gemini 2.5 Flash Image (Nano Banana) 로 생성.

---

### 🎯 비전

1. **Phase 1 (현재)**: 비주얼 + 오케스트레이션 레이어.
2. **Phase 2**: SaaS · PyPI 패키지 · 설치형 배포. 타깃은 **코드를 직접 치지 않는 도메인 전문가**.

Anthropic 과 관련 없음.

</details>

<details>
<summary><b>🇺🇸 English</b></summary>

<br>

OmniHarness lets **domain experts who don't write code directly** (planners, operators, field engineers) use Claude Code as a **dedicated team for their project**. Set your company name, industry, philosophy, and goal once, and:

1. The **orchestrator (LLM)** actually *designs* the agent team your project needs — real reasoning, not keyword matching.
2. Once you confirm, an **office floor plan** is drawn — every agent sits at their own desk.
3. As Claude Code runs, the owning agent's monitor lights up and live logs accumulate.
4. When an agent hits an ambiguous decision, the **Management-support lead (mgmt-lead)** translates the technical wording into plain language, then converts your answer back into something the agent can execute (two-way translation).
5. As knowledge accumulates, the **auditor** files **audit proposals** — new agents, features, retires, or refactors. Accepting actually mutates the roster.

> 📸 `(office floor-plan screenshot)` · 📸 `(Q&A translation screenshot)` · 🎬 `(audit proposal video)`

---

### 🚀 First-run experience

On first launch, a tutorial appears:
1. **Language picker** — 🇰🇷 / 🇺🇸 two large buttons. Everything else switches to that language.
2. **Welcome** — short intro to the office metaphor.
3. **Tab tour** — ten seconds on each of the eight tabs (Org · Activity · Questions · Requirements · Backlog · Audit · Knowledge · Reports).

After that, you land straight on the project list — pick an existing project or create a new one.

---

### 🧠 Core: LLM-driven team design

The old keyword heuristic was removed. With an API key:

- `ANTHROPIC_API_KEY` or `CLAUDE_CODE_USE_BEDROCK=1 + AWS_*` → the orchestrator actually reasons about your project and proposes a **project-specific team**.
- Proposed agents don't have to be in any catalog — LLM-invented `dev-<name>` / `<domain-name>` specs live inline in `mission.json` and render directly in the topology.
- No API key → the onboarding wizard shows a ⚠️ warning and falls back to the keyword heuristic.

The **reasoning** is shown right in the wizard — one line from the LLM on why this team fits *this* project.

> 📸 `(LLM team proposal screenshot)`

---

### 👥 Base team (shared across all projects)

| Tier | Role | Model | Purpose |
|---|---|---|---|
| 1 | `orchestrator` | opus | Triage, delegation, final HR call |
| 2 | `dev-lead` | opus | Coordinates feature-owning agents |
| 2 | `mgmt-lead` | opus | Two-way translation between user and agents |
| 2 | `eval-lead` | opus | UX · verify · security · domain-research pipeline |
| 3 | `reporter` · `hr` · `auditor` | sonnet | Management support (reports · roster health · audit) |
| 3 | 6 evaluators | sonnet | ux-reviewer · dev-verifier · user/admin-role-tester · security-auditor · domain-researcher |

When you create a project, the orchestrator proposes dev-\* / domain specialists *on top of* this base team.

---

### 🔄 Two-way Q&A translation

```
Agent posts the raw technical question    (pending_translation)
  ↓
mgmt-lead rewrites it in plain language   (pending_user)
  ↓
You answer freely in the UI               (pending_answer_translation)
  ↓
mgmt-lead converts it into a structured
instruction for the agent                 (answered)
  ↓
Agent receives an executable instruction
and resumes work
```

You don't need technical jargon, and agents never get vague instructions.

---

### 🔍 Audit · org changes

Not "self-evolution" — the **auditor** is a company role that periodically reviews the organization.

- **Knowledge**: every agent logs what it learned via `POST /api/knowledge`.
- **Audit proposals**: the auditor files new-agent / retire-agent / feature / refactor proposals via `POST /api/evolution`.
- **Accepted proposals actually mutate state**: accepting `new_agent` / `retire_agent` updates `mission.json`'s roster and shows up in the office scene immediately (not advisory-only).

**Edit permission model**: only the orchestrator edits an agent's `.md` config file. HR (`hr`) can *propose* adding or retiring, but needs unanimous approval from the orchestrator and the relevant team lead. Tie-breaker is the orchestrator.

> 📸 `(audit tab screenshot)`

---

### 🏢 Office scene

The main custom-mode view:

- **Multi-band wall/floor gradient** — each team room paints one wall + floor band per row of agents. Adding a new agent that pushes a new row auto-adjusts.
- **Stable sort** — "leads first, then alphabetical". Adding / retiring an agent doesn't shuffle existing members.
- **Sprite normalization** — each cell is size-, center-, and bottom-anchor normalized. A permanent white-background strip runs inside `_chroma_key`.
- **Right sidebar** — characters / MCPs / skills all open the same docked side panel. When open, the main content pushes left so the panel never overlaps.
- **Left TODO overlay** — ⚡Working · 📋Next · ✅Done. Click a row to expand with the actual task list plus a plain-language summary from mgmt-lead.

> 📸 `(sprite sheet example)` · 📸 `(TODO panel expanded)`

---

### ⚙️ Environment variables (.env)

Workspace-root `.env`. Copy `.env.example` and fill in what you need.

```bash
cp .env.example .env
```

- `ANTHROPIC_API_KEY` **or** `CLAUDE_CODE_USE_BEDROCK=1 + AWS_*` — required for LLM team proposal + the 💬 web-chat orchestrator
- `GEMINI_API_KEY` — for character / item art (Nano Banana / Gemini 2.5 Flash Image)
- `OMNIHARNESS_URL` — where the CLI hook POSTs (default `http://localhost:8082`)

---

### 🎨 Art asset generation (Gemini)

```bash
pip install google-genai
python OmniHarness/scripts/generate_assets.py
```

Generates:
- **Character sheets** — `/public/tiles/chars/<agent>-sheet.png` (4x4 pose grid)
- **Item tiles** — `/public/tiles/items/<id>.png` (desks, chairs, plants, water cooler, coffee machine, server rack, skill books)
- **Backdrop** — `/public/tiles/general/backdrop.png` (optional)

An automatic **consistency pass** runs after generation — Gemini Vision compares sheets and regenerates any that drift in pixel density / line weight / palette. The chroma-key stage now permanently strips near-white backgrounds too.

---

### ⚡ Quick start

```bash
# 1) Backend
cd OmniHarness/backend
pip install "fastapi[standard]" uvicorn pydantic
uvicorn app:app --host 0.0.0.0 --port 8081

# 2) Frontend
cd OmniHarness/frontend
npm install
npm run build

# 3) Open
open http://localhost:8081
```

First visit: tutorial → language pick → project list → new / existing → confirm team.

---

### 🔌 Connecting a consumer project

```bash
# From inside your consumer project, mirror the agent templates
python ../OmniHarness/scripts/sync_to.py .

# Wire hooks in .claude/settings.json so every Agent · Edit · Write · Bash
# event POSTs to OmniHarness(:8081).
```

Running `claude` inside your consumer project now streams live state into the viewer.

---

### 🗂️ Layout

```
OmniHarness/
├── backend/
│   └── app.py                         # FastAPI — topology · questions ·
│                                      # evolution · knowledge · projects ·
│                                      # LLM team proposal · mission
├── frontend/src/
│   ├── App.jsx                        # State machine: project → wizard → office
│   ├── ProjectList.jsx                # Project list / create (+ lang picker)
│   ├── Onboarding.jsx                 # Mission → LLM team proposal → confirm
│   ├── OfficeScene.jsx                # Office floor plan + left TODO overlay
│   ├── Tutorial.jsx                   # First-run tutorial (lang pick + tab tour)
│   ├── HUD.jsx                        # Cost · guide · KO/EN
│   ├── Character.jsx · Sprite.jsx     # Character rendering
│   ├── AgentPanel.jsx                 # Character sidebar (md view + permission notice)
│   ├── McpPanel.jsx                   # MCP/skill sidebar (same form)
│   ├── TabPanel.jsx · Questions.jsx · Evolution.jsx · ...
│   └── i18n.js                        # KO/EN translation table (default = EN)
├── templates/
│   ├── agents/                        # Agent templates (project-agnostic)
│   └── proposals/                     # Audit proposal storage
├── projects/                          # Per-project mission.json (incl. custom specs)
└── scripts/
    ├── sync_to.py                     # Templates → <consumer>/.claude/agents/
    ├── hook_to_omniharness.py         # stdin → viewer bridge
    └── generate_assets.py             # Gemini art gen + chroma-key + white-bg strip
```

---

### 🖼️ Assets

- **Character sprites** — SVG by default. Drop a high-res PNG sheet at `/tiles/chars/<agent>-sheet.png` to override just that agent. Size / center / bottom-anchor normalization runs automatically.
- **Item tiles** — desks, chairs, plants, MCP appliances, skill books, freely composable.
- **All art** — generated with Gemini 2.5 Flash Image (Nano Banana).

---

### 🎯 Vision

1. **Phase 1 (current)**: visual + orchestration layer.
2. **Phase 2**: SaaS · PyPI package · installer distribution. Target audience: **domain experts who don't write code directly**.

Not affiliated with Anthropic.

</details>

---

## 📅 Updates / 업데이트

Reverse chronological. Each entry is a short "why" — the commit log has the "how".

### `v1.1` — 2026-04-19 — **LLM team design · Tutorial · Unified sidebars**
- 🧠 **Real LLM team proposal** via Anthropic / Bedrock. The orchestrator *reasons* about the project and can invent project-specific agents outside the fixed catalog. Keyword heuristic kept only as a fallback with a ⚠️ warning in the wizard.
- 🎓 **First-run Tutorial overlay** — language picker (🇰🇷 / 🇺🇸) + 8-tab guided tour. Persists via localStorage, runs exactly once.
- 🏢 **Custom-only focus** — General viewer mode hidden, boot goes straight into project list.
- 📊 **Left TODO · Next · Done overlay** — click any row to expand; each task gets a mgmt-lead-voice plain-language summary.
- 🎨 **Office scene polish** — multi-band wall/floor gradient per row, stable intra-team sort (lead first then alphabetical), sprite normalization (size · center · bottom-anchor), permanent white-bg strip in `_chroma_key`.
- 🪟 **Unified right sidebar** — character / MCP / skill clicks all open the same docked form. When open, main content pushes left instead of overlapping.
- 🔑 **Orchestrator-only edits** — AgentPanel shows the agent's `.md` config with a permission notice; HR can *propose* add / retire with unanimous approval from orchestrator + team lead (tiebreak: orchestrator).
- ✅ **Accepted audit proposals now mutate the real roster** — `new_agent` / `retire_agent` decisions actually update `mission.json`.
- 🌐 **i18n cleanups** — `DEFAULT_LANG='en'`, "자가진화" → "감사" (Audit as a company role), "확정하고 시작" → "확인", `대기`/`대기중` merged to single `대기`.
- 📚 README: bilingual `<details>` toggle, icons on every heading, this changelog section added.

### `v1.0` — 2026-04-19 — **Unified viewer · 22-character pixel cast**
- 🎭 Nano-Banana-generated 4×4 pose sprite sheets for all 22 agents.
- 🧭 General viewer (traced subagents / MCPs / skills from a single Claude Code session) alongside the Custom office scene.
- ☕ Canteen with MCP appliances (fridge / shell / coffee / printer / server-rack) and skill books.
- 💬 Web-chat orchestrator via Anthropic SDK or Bedrock.

### `v0.4` — 2026-04-19 — **FabCanvas-aligned 26-agent roster · Dark org-tree viewer**
- 👥 Expanded roster tailored for the first consumer (FabCanvas).
- 🌲 Dark-theme organization tree with drill-down per team.

### `v0.3` — 2026-04-18 — **Initial public commit**
- 📜 FastAPI backend + React viewer skeleton.
- 🔌 Hook bridge (`scripts/hook_to_omniharness.py`) for Claude Code state → viewer.

---

<sub>⚖️ OmniHarness is an independent project. Not affiliated with Anthropic. "Claude" and "Claude Code" are trademarks of Anthropic.</sub>
