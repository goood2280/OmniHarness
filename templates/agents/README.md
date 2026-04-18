# OmniHarness Agent Templates

This directory is the **canonical source of truth** for the Claude Code agent harness pattern.

Consumer projects (currently: `FabCanvas.ai/`) get these templates mirrored into their own `.claude/agents/` via `OmniHarness/scripts/sync_to.py` (to be built). FabCanvas.ai is the running harness; OmniHarness is the spec.

## Organization Chart

```
                        ┌───────────────────────────┐
                        │   orchestrator (총괄)     │   opus
                        └───────────┬───────────────┘
                ┌───────────────────┼───────────────────┐
                │                   │                   │
         ┌──────▼──────┐    ┌───────▼──────┐    ┌───────▼──────┐
         │  dev-lead   │    │  mgmt-lead   │    │  eval-lead   │   opus
         └──────┬──────┘    └──────┬───────┘    └──────┬───────┘
                │                  │                   │
     ┌──────────┼────────┐    ┌────┴─────┐    ┌────────┼────────┬────────┬───────────┐
     │          │        │    │          │    │        │        │        │           │
  (BE팀)     (FE팀)              reporter  hr  ux-reviewer  dev-verifier user-tester admin-tester
  be-*       fe-*                                  feature-auditor     industry-researcher
  sonnet     sonnet              sonnet            sonnet
```

## Tier & Model

| Tier | Role | Model |
|---|---|---|
| 1 | orchestrator | `opus` (Opus 4.7) |
| 2 | dev-lead, mgmt-lead, eval-lead | `opus` |
| 3 | all team members (be-*, fe-*, reporter, hr, ux-reviewer, dev-verifier, user-tester, admin-tester, feature-auditor, industry-researcher) | `sonnet` (Sonnet 4.6) by default |

HR has authority to **propose** downgrading a member to `haiku` if workload permits — actual model change requires the consultation gate (below).

## HR Consultation Gate

HR cannot unilaterally add, remove, or reassign agents. Any such change must pass through:

1. **HR proposes** → writes a proposal to `templates/proposals/<YYYY-MM-DD>-<slug>.md`
2. **Team lead discusses** → the affected team's lead reviews
3. **Orchestrator discusses** → orchestrator weighs in
4. **Decision:**
   - If unanimous (HR + team lead + orchestrator) → execute (Write/Edit `.claude/agents/*`)
   - If not unanimous → **Orchestrator's decision is final**

## Roster (MVP — 18 agents)

| Team | Files |
|---|---|
| Top | `orchestrator.md` |
| Leads | `dev-lead.md`, `mgmt-lead.md`, `eval-lead.md` |
| 개발1팀 (Backend) | `be-dashboard.md`, `be-filebrowser.md`, `be-tracker.md` |
| 개발2팀 (Frontend) | `fe-dashboard.md`, `fe-filebrowser.md`, `fe-tracker.md` |
| 경영지원팀 | `reporter.md`, `hr.md` |
| 평가팀 | `ux-reviewer.md`, `dev-verifier.md`, `user-tester.md`, `admin-tester.md`, `feature-auditor.md`, `industry-researcher.md` |

HR may propose additional agents (e.g., `be-splittable`, `be-tablemap`, `fe-admin`, `fe-ml`) over time via the consultation gate.

## File Format

Each agent file is a standard Claude Code subagent definition:

```markdown
---
name: agent-name
description: When this agent should be invoked (1-2 sentences)
model: opus | sonnet | haiku
tools: Read, Grep, ...
---

System prompt body. Describes role, responsibilities, collaboration protocol,
and constraints. Written in Korean (user preference) with English tool names.
```

## Conventions

- **Names** use kebab-case matching the filename (minus `.md`).
- **Cross-references** use names, not filenames (e.g., "consult `dev-lead`").
- **Paths** in system prompts assume the consumer project is the cwd. So `backend/routers/dashboard.py` refers to `<consumer>/backend/routers/dashboard.py`.
- **No secrets, no absolute paths** in agent bodies — templates must be portable across consumer projects.
