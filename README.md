# OmniHarness

> A pixel-office viewer + structural pattern for running Claude Code as a coordinated team of subagents.

OmniHarness is two things in one repo:

1. **A harness pattern** — an opinionated `.claude/agents/` layout (orchestrator + 3 teams: 개발 / 경영지원 / 평가) that any consumer project can mirror via `scripts/sync_to.py`.
2. **A live pixel-office viewer** — a browser UI that watches real Claude Code work happen in a consumer project (via hooks) and renders it as a 2D office scene: desks, plants, appliances, characters, each lighting up with a ⚡ halo when actually working.

It's not "an agent that builds your app." It's the stage on which Claude Code builds your app, with visible agent roles, a shared mission at the top, a growing activity log, and a question→answer loop for decisions only a human can make.

---

## Why

Working on a single codebase with Claude Code is easy. Working on a codebase through **many parallel, specialized subagents** — a backend team, a frontend team, testers, a reporter, an HR agent that can propose adding/removing other agents — is powerful but hard to *see*.

OmniHarness makes it seeable. The moment you invoke a subagent in a consumer project, that agent's chair lights up in the office. When it finishes, it goes idle. When it hits an ambiguity it can't resolve, the question lands in the Questions tab — first raw, then translated into friendly Korean by the mgmt-lead, waiting for your answer.

## The 18-agent roster (MVP)

| Tier | Role | Model |
|---|---|---|
| 1 — 총괄 | `orchestrator` | opus |
| 2 — 팀 리드 | `dev-lead` · `mgmt-lead` · `eval-lead` | opus |
| 3 — 개발1팀 Backend | `be-dashboard` · `be-filebrowser` · `be-tracker` | sonnet |
| 3 — 개발2팀 Frontend | `fe-dashboard` · `fe-filebrowser` · `fe-tracker` | sonnet |
| 3 — 경영지원팀 | `reporter` · `hr` | sonnet |
| 3 — 평가팀 | `ux-reviewer` · `dev-verifier` · `user-tester` · `admin-tester` · `feature-auditor` · `industry-researcher` | sonnet |

HR cannot unilaterally add/remove agents — any proposal goes through a 3-way consultation (HR + the team's lead + orchestrator). If not unanimous, the orchestrator's decision is final.

## Features

- **Pixel-art office** — 4 quadrants (총괄 / 평가팀 / 개발팀 / 경영지원팀) + kitchen strip (MCPs). Team leads sit at the top of each area; members below. Built on LimeZu's Modern Office tiles and Legacy character sprites.
- **Live state** — each agent has `idle | working | waiting`; a pulsing yellow halo + `!` badge marks working agents. Pigeons carrying folders scale with the working count.
- **Mission banner** — the first thing any new project sets: industry / philosophy / goal. These are the shared purpose for every agent.
- **Activity log** — ring-buffer of recent events. Driven by real Claude Code hooks, or by a demo cycler when `DEMO=ON`.
- **Questions** — when an agent hits a decision only a human should make, it posts a raw technical question. The mgmt-lead (LLM step) translates it into friendly language; the user answers in the UI; the resolution flows back into the dev loop.
- **Reports** — when enough meaningful changes accumulate, the reporter agent publishes a short Korean-language summary, saved to `reports/`.
- **Cost tracker** — cumulative API cost in the HUD, broken down by model. Based on Anthropic's 2026 pricing table.

## Quick start

```bash
# 1) Backend
cd OmniHarness/backend
pip install "fastapi[standard]" uvicorn pydantic
uvicorn app:app --host 0.0.0.0 --port 8081

# 2) Frontend
cd OmniHarness/frontend
npm install
npm run build        # or `npm run dev` for hot reload

# 3) Open
# http://localhost:8081
```

First visit forces you to fill the **Mission** overlay (업종 / 철학 / 목표). After that the office loads with all 18 agents idle. Turn `DEMO` on in the HUD to see simulated activity, or wire hooks (below) to see the real thing.

## Wiring it into your project

From inside your consumer project (e.g. `FabCanvas.ai`):

```bash
# 1) Mirror the agent roster into your .claude/agents/
python ../OmniHarness/scripts/sync_to.py .

# 2) Drop the hook bridge into your .claude/settings.json — see
#    FabCanvas.ai/.claude/settings.json for a full example. Each tool
#    event (Agent invocations, Edit/Write/Bash) will POST to
#    http://localhost:8081 so the viewer lights up.
```

The hook script (`scripts/hook_to_omniharness.py`) is defensive: if the viewer is offline, Claude Code is never blocked.

## Layout

```
OmniHarness/
├── backend/
│   └── app.py                # FastAPI: topology / states / activity / questions / reports / cost / mission
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── PixelOffice.jsx   # canvas scene
│   │   ├── MissionBanner.jsx
│   │   ├── HUD.jsx
│   │   ├── TabPanel.jsx → ActivityLog / Questions / Reports
│   │   ├── AgentPanel.jsx
│   │   └── styles.css
│   └── public/tiles/          # LimeZu sprites + per-agent character sprites
├── templates/
│   ├── agents/                # 18 canonical .md files — the source of truth
│   └── proposals/             # HR-produced add/remove proposals
├── scripts/
│   ├── sync_to.py             # mirror templates → <consumer>/.claude/agents/
│   └── hook_to_omniharness.py # stdin-reading hook bridge
└── reports/                   # persisted reporter output
```

## Assets

Character and environment sprites are from [LimeZu](https://limezu.itch.io/)'s **Modern Office** and **Interiors** tilesets, used under their license. Only a curated subset (33 PNGs) is committed under `frontend/public/tiles/` — the full packs are not redistributed.

## Status

Early. The 18-agent roster is the MVP scope and HR has authority to propose expansions. Viewer is functional; hook→real-work integration is wired but benefits from more hook points as Claude Code exposes them.

Not affiliated with Anthropic.
