# OmniHarness

> Visualization + orchestration layer for running Claude Code as a coordinated team of subagents.

Two things in one repo:

1. **A harness pattern** — an opinionated `.claude/agents/` layout (orchestrator + 3 leads + dev team + domain specialists + eval + mgmt) that any consumer project can mirror via `scripts/sync_to.py`.
2. **A live org-tree viewer** — a browser UI that watches real Claude Code work happen in a consumer project (via hooks) and renders it as a dark-themed pixel-chibi org chart. Click an agent to inspect its system prompt, tools, and current state. Wheel-zoom and drag-pan.

It's not "an agent that builds your app." It's the stage on which Claude Code builds your app, with visible agent roles, a shared mission at the top, a growing activity log, and a question→answer loop for decisions only a human can make.

---

## What's in this release (v0.4)

- **26-agent roster** reorganized for FabCanvas.ai (semiconductor fab dev-stage data analysis), one of the first concrete consumer projects. Domain-specific specialists: `process-tagger`, `causal-analyst`, `dvc-curator`, `adapter-engineer`.
- **Org-tree viewer** on a dark background. Characters are LimeZu Legacy chibi sprites, one per agent. Team clusters in color-coded rounded boxes.
- **Mission banner** at top: company / industry / philosophy / goal (the shared purpose every agent optimizes for).
- **Tab panel** below the tree: 조직도 (drill-down) / Activity / Questions / Requirements / Backlog / Reports.
- **Questions flow** — when an agent hits an ambiguous decision, `mgmt-lead` translates the raw technical question into friendly language; you answer in the UI; the answer flows back into the dev loop.
- **Requirements** — send free-form requirements to the orchestrator; filter by bucket (waiting / working / done / cancelled); cancel anything still waiting.
- **Reports** — reporter agent publishes summaries; markdown body renders with headings/bold/bullets/blockquote.
- **Cost tracker** — HUD shows cumulative USD spend (tier-aware token estimates: Opus 2500/1500, Sonnet 900/450, Haiku 600/300 tokens per invocation). Resets on backend restart.
- **KO/EN language toggle** — every user-facing string (including all 26 agent display names) flips.
- **Bedrock GUIDE** — ☁ button in the HUD opens a modal with the 6-section setup flow (model access → AWS creds → env vars → OmniHarness wiring → verification). Bedrock is registered as an enabled provider.
- **Hook bridge** — `scripts/hook_to_omniharness.py` listens to Claude Code's tool-use events from `FabCanvas.ai/.claude/settings.json` and POSTs them to the viewer. No viewer? Hooks silently no-op so Claude Code is never blocked.

## The 26-agent roster

| Tier | Role | Model |
|---|---|---|
| 1 — 총괄 | `orchestrator` | opus |
| 2 — 팀 리드 | `dev-lead` · `mgmt-lead` · `eval-lead` | opus |
| 3 — 개발팀 (feature owners, full-stack) | `dev-dashboard` · `dev-spc` · `dev-wafer-map` · `dev-ml` · `dev-ettime` · `dev-tablemap` · `dev-tracker` · `dev-filebrowser` · `dev-admin` · `dev-messages` | sonnet |
| 3 — 도메인 전문 | `process-tagger` · `causal-analyst` · `dvc-curator` · `adapter-engineer` | sonnet |
| 3 — 경영지원팀 | `reporter` · `hr` | sonnet |
| 3 — 평가팀 | `ux-reviewer` · `dev-verifier` · `user-role-tester` · `admin-role-tester` · `security-auditor` · `domain-researcher` | sonnet |

The domain specialists own read-only rule tables (causal matrix, process-area map, DVC direction rules, adapter profiles). Dev feature-owners consult them via `dev-lead`. HR cannot unilaterally add or remove agents — a 3-way consultation (HR + affected team lead + orchestrator) is required; tiebreaker goes to the orchestrator.

## Quick start

```bash
# 1) Backend
cd OmniHarness/backend
pip install "fastapi[standard]" uvicorn pydantic
uvicorn app:app --host 0.0.0.0 --port 8081

# 2) Frontend
cd OmniHarness/frontend
npm install
npm run build           # or `npm run dev` for hot reload

# 3) Open http://localhost:8081
```

First visit forces the Mission modal (company / industry / philosophy / goal). After that the viewer loads idle — 0 working agents, $0 cost. Agents only light up when real Claude Code work happens in a wired consumer project.

## Wiring into a consumer project

From the consumer project (e.g. `FabCanvas.ai`):

```bash
# 1) Mirror the agent roster into your .claude/agents/
python ../OmniHarness/scripts/sync_to.py .

# 2) Copy FabCanvas.ai/.claude/settings.json as your template — it POSTs
#    every Agent/Edit/Write/Bash event to http://localhost:8081.
```

When you then run `claude` inside the project directory, the viewer will light up whichever subagent Claude calls, append activity, and accrue cost.

## Layout

```
OmniHarness/
├── backend/
│   └── app.py                    # FastAPI: topology / states / activity / questions /
│                                 # reports / cost / mission / requirements / backlog /
│                                 # mcps / org / providers / guide/bedrock
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── OrgTree.jsx           # main dark-themed org chart with zoom + drag
│   │   ├── MissionBanner.jsx     # company · industry · philosophy · goal
│   │   ├── HUD.jsx               # agents · spend · model mix · GUIDE · KO/EN
│   │   ├── TabPanel.jsx
│   │   ├── OrgChart.jsx          # drill-down tab: teams → members → prompt
│   │   ├── ActivityLog.jsx
│   │   ├── Questions.jsx         # agent→user translated Q&A
│   │   ├── RequirementInput.jsx  # user→orchestrator requirements + cancel
│   │   ├── Backlog.jsx
│   │   ├── Reports.jsx           # markdown-rendered summaries
│   │   ├── AgentPanel.jsx        # click an agent → side drawer
│   │   ├── BedrockGuide.jsx      # ☁ GUIDE modal
│   │   ├── McpPanel.jsx
│   │   ├── i18n.js               # KO + EN translations (incl. agent display names)
│   │   └── styles.css
│   └── public/tiles/              # LimeZu Legacy chibi sprites + office tiles
│       └── chars/                 # 26 per-agent sprites
├── templates/
│   ├── agents/                    # 26 canonical .md files — source of truth
│   └── proposals/                 # HR-produced add/remove proposals
├── scripts/
│   ├── sync_to.py                 # mirror templates → <consumer>/.claude/agents/
│   └── hook_to_omniharness.py     # stdin-reading bridge for Claude Code hooks
└── reports/                       # persisted reporter output (gitignored)
```

## Assets

Character and environment sprites are from [LimeZu](https://limezu.itch.io/)'s **Modern Office** and **Interiors (Legacy characters)** tilesets, used under their license. Only a curated subset is committed under `frontend/public/tiles/` — the full packs are not redistributed.

## Vision

1. **Phase 1 (current)** — visualization + orchestration layer on top of Claude Code.
2. **Phase 2** — commercial distribution. The target audience is **domain experts who don't code** (e.g. semiconductor process engineers). Distribution options: SaaS, PyPI package, or a packaged product. UX is designed around a friendly mission banner and a question-translation loop so non-technical users can steer the system.

Not affiliated with Anthropic.
