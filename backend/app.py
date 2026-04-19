"""OmniHarness Viewer — FastAPI backend (v0.5).

Generic, project-agnostic harness for visualizing Claude Code subagents.
The user configures a mission (company / industry / philosophy / goal),
the orchestrator proposes a team structure, and the viewer shows agents
at desks in an office floor-plan. As Claude Code runs, hooks stream
activity events here, monitors light up, and knowledge accumulates.

Endpoints:
- GET  /api/topology                   org chart + per-agent state
- POST /api/agents/{name}/state        push live state (from hooks)

- GET/POST /api/activity               ring buffer of events
- GET/POST /api/questions              agent → mgmt-lead → user
- POST /api/questions/{id}/translate   mgmt-lead writes friendly text
- POST /api/questions/{id}/answer      user writes free-form answer
- POST /api/questions/{id}/answer/translate   mgmt-lead converts user
                                              answer into structured input
- GET/POST /api/reports                reporter summaries

- GET  /api/mission                    current mission + team config
- POST /api/mission                    save mission (pre-team-setup)
- POST /api/mission/propose_team       orchestrator proposes roster
- POST /api/mission/confirm_team       user confirms and locks roster

- GET  /api/requirements               user → orchestrator queue
- POST /api/requirements               create
- POST /api/requirements/{id}/status   update
- POST /api/requirements/{id}/cancel   cancel

- GET  /api/backlog                    (empty until Claude Code seeds it)
- GET  /api/cost                       cumulative USD spend

- GET  /api/mcps                       MCP descriptors
- GET  /api/org                        hierarchical drill-down
- GET  /api/providers                  LLM provider presets
- GET  /api/guide/bedrock              Bedrock setup guide sections

- GET  /api/knowledge                  accumulated learnings (self-evo)
- POST /api/knowledge                  agent appends a learning
- GET  /api/evolution                  pending proposals (new agents,
                                        feature ideas)
- POST /api/evolution                  agent proposes an evolution step
- POST /api/evolution/{id}/decision    user accepts/rejects

- /                                    serves the Vite-built SPA

Run: cd OmniHarness/backend && uvicorn app:app --host 0.0.0.0 --port 8081
"""
from __future__ import annotations

import json
import os
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Literal


# ── .env loader (no external deps) — walks up from this file looking
#    for a .env file and loads KEY=value pairs into os.environ. This
#    lets users drop their GEMINI / ANTHROPIC / AWS keys in one place
#    at the repo root.
def _bootstrap_env():
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        f = parent / ".env"
        if not f.exists():
            continue
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
        except Exception:
            pass
        break


_bootstrap_env()

import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Active coordinator (state-transition playback engine). Imported here
# only for the start/stop/list endpoints below — the module itself
# does a late `import app` to read/write our in-memory tables.
import coordinator as _coordinator
# Periodic audit pass (감사). Fires every OMNI_AUDIT_EVERY coordinator
# completions, or on-demand via /api/audit/run. Late-imports app.* the
# same way coordinator.py does.
import audit as _audit
# mgmt-lead translator — raw 질문을 도메인 전문가 친화적으로 풀어쓴다.
# ANTHROPIC_API_KEY 있으면 claude-haiku-4-5 호출, 없으면 heuristic.
import translator as _translator

ROOT = Path(__file__).parent.parent
TEMPLATES = ROOT / "templates" / "agents"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR = ROOT / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
# Legacy single-file mission.json at the root — imported into a project
# on first boot so existing users don't lose their setup.
LEGACY_MISSION_FILE = ROOT / "mission.json"
ACTIVE_PROJECT_FILE = ROOT / ".active_project"
APP_MODE_FILE = ROOT / ".app_mode"  # "general" | "custom" | ""
KNOWLEDGE_FILE_LEGACY = ROOT / "knowledge.json"

# ── Roles (slimmed 2026-04-19) ───────────────────────────────────────
# Only real multi-agent value survives: context-isolation (dev-lead) and
# independent-perspective reviewers. mgmt-lead/reporter/hr/eval-lead are
# removed — orchestrator writes Questions/Reports in plain language
# directly, and roster changes go through user approval instead of an
# HR proposal gate.
#
# Domain rules (process_area / causal / dvc / adapter) are reference
# documents under projects/<proj>/knowledge/, not agents. The viewer
# renders them as bookshelf/cabinet sprites, not characters.
#
# Each entry: name → (team_id, label_color)
BASE_ROLES: dict[str, tuple[str, str]] = {
    "orchestrator":      ("top",   "#E87722"),
    "dev-lead":          ("dev",   "#7cc7e8"),
    "ux-reviewer":       ("eval",  "#ff9b9b"),
    "dev-verifier":      ("eval",  "#e57373"),
    "user-role-tester":  ("eval",  "#a56c4c"),
    "admin-role-tester": ("eval",  "#8c5a3c"),
    "security-auditor":  ("eval",  "#7a6650"),
    "domain-researcher": ("eval",  "#6c5a44"),
}

# No catalog fan-out anymore. dev-lead is a single full-stack agent;
# feature areas live as activity-log tags ("dashboard", "spc", ...) on
# dev-lead's work stream. Kept for backward compatibility with old
# mission.json payloads — always empty for new projects.
DEV_CATALOG: list[str] = []
DOMAIN_CATALOG: list[str] = []

# Knowledge documents live under projects/<proj>/knowledge/*.md. These
# are the canonical slugs the viewer renders as bookshelf items and the
# orchestrator/dev-lead reads directly.
KNOWLEDGE_CATALOG: list[str] = [
    "process_area_rules",
    "causal_direction_matrix",
    "dvc_parameter_directions",
    "adapter_mapping_rules",
]

TEAMS = [
    {"id": "top",       "label_ko": "총괄",          "label_en": "HQ"},
    {"id": "dev",       "label_ko": "개발",          "label_en": "Dev"},
    {"id": "eval",      "label_ko": "리뷰어",        "label_en": "Reviewers"},
    {"id": "knowledge", "label_ko": "지식 자료",     "label_en": "Knowledge"},
]

State = Literal["idle", "working", "waiting"]

# ── Pricing (approximate 2026 rates, USD per 1M tokens) ──────────────
PRICING = {
    # Anthropic Claude 4.x
    "opus":     {"in": 15.0,  "out": 75.0},
    "sonnet":   {"in": 3.0,   "out": 15.0},
    "haiku":    {"in": 1.0,   "out": 5.0},
    # OpenAI (대표 모델 2종; OpenAI 요금은 실시간 변동 — 대략치)
    "gpt-4o":      {"in": 2.5,  "out": 10.0},
    "gpt-4o-mini": {"in": 0.15, "out": 0.6},
    # Google Gemini
    "gemini-2.5-pro":   {"in": 1.25, "out": 10.0},
    "gemini-2.5-flash": {"in": 0.3,  "out": 2.5},
}

# ── In-memory state ──────────────────────────────────────────────────
STATES: dict[str, State] = {}
COST_TOTAL: float = 0.0
COST_BY_MODEL: dict[str, float] = {k: 0.0 for k in PRICING.keys()}
COST_BY_AGENT: dict[str, dict] = {}
TOKENS_BY_MODEL: dict[str, dict] = {k: {"in": 0, "out": 0} for k in PRICING.keys()}

ACTIVITY: deque = deque(maxlen=300)

# Provider API keys — user-supplied via UI. Persisted to _state/state.json.
# On load we also inject into os.environ so the rest of the codebase
# (translator._llm_call, coordinator stubs, _detect_provider) keeps
# working unchanged. Empty / missing → deleted from the dict and env.
#   anthropic | openai | gemini → API_KEY string
#   bedrock                    → "1" if CLAUDE_CODE_USE_BEDROCK is on
PROVIDER_KEYS: dict[str, str] = {}

# Maps the UI key slot → actual os.environ name we mirror into.
# Bedrock easy-connect: three AWS creds slots + one toggle. On Windows
# we also persist via `setx` (see /api/providers/aws/persist_windows)
# so values survive a reboot without needing .env editing.
#
# Heterogeneous providers (Gemini image, ElevenLabs voice, …) sit
# alongside Claude here — OmniHarness lets the user wire each one once
# so subagents like `asset-maker` (image) or `voice-io` (TTS/STT) can
# dispatch to the provider that actually handles that modality well.
_PROVIDER_ENV_MAP: dict[str, str] = {
    "anthropic":             "ANTHROPIC_API_KEY",
    "openai":                "OPENAI_API_KEY",
    "gemini":                "GEMINI_API_KEY",
    "elevenlabs":            "ELEVENLABS_API_KEY",
    "falai":                 "FAL_KEY",
    "bedrock":               "CLAUDE_CODE_USE_BEDROCK",
    "aws_access_key_id":     "AWS_ACCESS_KEY_ID",
    "aws_secret_access_key": "AWS_SECRET_ACCESS_KEY",
    "aws_region":            "AWS_REGION",
}


def _apply_provider_keys_to_env() -> None:
    """Mirror PROVIDER_KEYS into os.environ. Called on load and after
    every POST so translator / chat code paths see the latest value
    without restart."""
    for slot, envname in _PROVIDER_ENV_MAP.items():
        val = PROVIDER_KEYS.get(slot)
        if val:
            os.environ[envname] = val
        # If the user cleared the UI slot we do NOT pop os.environ[envname]
        # — a .env / shell export may legitimately still own that slot.
        # POST handler removes it explicitly when asked.


def _mask_key(val: str) -> str:
    """Return 'sk-…abcd' style mask for display. None/empty stays None."""
    if not val:
        return ""
    s = str(val)
    if len(s) <= 6:
        return "…" + s[-2:]
    return s[:3] + "…" + s[-4:]


QUESTIONS: list[dict] = []
REPORTS: list[dict] = []
REQUIREMENTS: list[dict] = []
BACKLOG: list[dict] = []
EVOLUTION: list[dict] = []

# 감사(audit) 루프 카운터 — coordinator 런 완료마다 +1, OMNI_AUDIT_EVERY
# 회마다 audit.run_audit_pass_async() 를 비동기로 돌린다.
COORDINATOR_COMPLETED: int = 0


def _next_short_q_id() -> str:
    """Return next ``Q###`` short id, scanning QUESTIONS for the highest
    existing numeric suffix. Monotonic: even after deletions we never
    reuse a prior number within a single process lifetime's view of the
    current list (ids live in-list so re-scan is correct on boot too)."""
    hi = 0
    for q in QUESTIONS:
        sid = (q or {}).get("short_id") or ""
        if isinstance(sid, str) and sid.startswith("Q") and sid[1:].isdigit():
            try:
                n = int(sid[1:])
                if n > hi:
                    hi = n
            except ValueError:
                pass
    return f"Q{hi + 1:03d}"


def _backfill_short_q_ids() -> None:
    """On boot, assign ``Q001``, ``Q002`` … to any QUESTIONS entry that
    is missing ``short_id``. Preserves existing short_ids so any value a
    user already memorised (e.g. ``Q042``) stays stable across restarts.
    We iterate oldest-first (QUESTIONS is newest-first; reversed())."""
    used = set()
    for q in QUESTIONS:
        sid = (q or {}).get("short_id")
        if isinstance(sid, str) and sid:
            used.add(sid)
    counter = 1
    for q in reversed(QUESTIONS):
        if q.get("short_id"):
            continue
        while f"Q{counter:03d}" in used:
            counter += 1
        sid = f"Q{counter:03d}"
        q["short_id"] = sid
        used.add(sid)
        counter += 1


def _backfill_translate_passthrough() -> None:
    """Passthrough 모드에서 부팅 시점에 ``pending_translation`` 상태로
    고여있는 질문들을 즉시 ``pending_user`` 로 승격해 사용자가 볼 수
    있게 한다. translator.simplify() 로 raw 를 풀어써서 translated 에
    넣는다 — ANTHROPIC_API_KEY 있으면 LLM, 없으면 heuristic. 실패하면
    raw 를 그대로 복사해 최소한 화면에는 뭔가 뜨게 한다.
    OMNI_TRANSLATE_PASSTHROUGH=0 이면 비활성."""
    passthrough = os.environ.get("OMNI_TRANSLATE_PASSTHROUGH", "1") in ("1", "true", "True")
    if not passthrough:
        return
    for q in QUESTIONS:
        if q.get("status") == "pending_translation":
            if not q.get("translated"):
                raw = q.get("raw", "")
                try:
                    q["translated"] = _translator.simplify(raw, {"agent": q.get("agent")})
                except Exception:
                    q["translated"] = raw
            q["status"] = "pending_user"

# ── 영속화 경로 ─────────────────────────────────────────────────────
# 서버 재기동에도 살아남아야 할 상태는 여기에 json dump.
_STATE_DIR = Path(__file__).parent / "_state"
_STATE_PATH = _STATE_DIR / "state.json"


def _known_agent_names() -> list[str]:
    """BASE + DEV_CATALOG + DOMAIN_CATALOG. Slimmed in 2026-04-19 —
    BASE is now 8 agents (orchestrator + dev-lead + 6 reviewers), and
    the catalogs are empty. Kept for API-shape compatibility."""
    return list(BASE_ROLES.keys()) + list(DEV_CATALOG) + list(DOMAIN_CATALOG)


def _save_state() -> None:
    """모든 mutation 함수 끝에서 호출. 저부하라 debounce 없음."""
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "requirements": REQUIREMENTS,
            "activity": list(ACTIVITY),
            "backlog": BACKLOG,
            "questions": QUESTIONS,
            "reports": REPORTS,
            "agent_states": STATES,
            "cost_total": COST_TOTAL,
            "cost_by_model": COST_BY_MODEL,
            "cost_by_agent": COST_BY_AGENT,
            "tokens_by_model": TOKENS_BY_MODEL,
            "provider_keys": PROVIDER_KEYS,
        }
        _STATE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        # 쓰기 실패해도 런타임은 계속 — 다음 mutation 에서 재시도.
        pass


def _load_state() -> None:
    """부팅 시 1회. 파일 없으면 조용히 스킵."""
    global ACTIVITY, COST_TOTAL
    if not _STATE_PATH.exists():
        return
    try:
        data = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    REQUIREMENTS[:] = list(data.get("requirements") or [])
    BACKLOG[:] = list(data.get("backlog") or [])
    QUESTIONS[:] = list(data.get("questions") or [])
    REPORTS[:] = list(data.get("reports") or [])
    ACTIVITY = deque(list(data.get("activity") or []), maxlen=300)
    STATES.clear()
    STATES.update(data.get("agent_states") or {})
    COST_TOTAL = float(data.get("cost_total") or 0.0)
    COST_BY_MODEL.update(data.get("cost_by_model") or {})
    COST_BY_AGENT.update(data.get("cost_by_agent") or {})
    for k, v in (data.get("tokens_by_model") or {}).items():
        if k in TOKENS_BY_MODEL and isinstance(v, dict):
            TOKENS_BY_MODEL[k].update(v)
    # Provider keys persisted from UI — re-inject into os.environ so the
    # translator and chat paths see them on cold boot, same as if the
    # user had exported them in their shell.
    PROVIDER_KEYS.clear()
    for k, v in (data.get("provider_keys") or {}).items():
        if isinstance(v, str) and v and k in _PROVIDER_ENV_MAP:
            PROVIDER_KEYS[k] = v
    _apply_provider_keys_to_env()
    # Migrate: any pre-existing QUESTIONS without short_id get one now.
    _backfill_short_q_ids()
    _backfill_translate_passthrough()


_load_state()

# KNOWN 에이전트 프리시드: 파일에 state 있으면 유지, 없으면 idle.
for _n in _known_agent_names():
    STATES.setdefault(_n, "idle")

DEFAULT_MISSION = {
    "company": "",
    "industry": "",
    "philosophy": "",
    "goal": "",
    "placeholder": True,
    # Team roster — set by /api/mission/confirm_team
    "dev_agents": [],
    "domain_agents": [],
    "team_confirmed": False,
    # Proposed but not yet confirmed
    "proposed_dev_agents": [],
    "proposed_domain_agents": [],
    "proposal_reason": "",
}


# ── Models ───────────────────────────────────────────────────────────
class StateUpdate(BaseModel):
    state: State


class ActivityEvent(BaseModel):
    agent: str
    kind: str
    detail: str


class QuestionIn(BaseModel):
    agent: str
    raw: str
    context: str | None = None


class QuestionTranslate(BaseModel):
    translated: str
    translator: str = "mgmt-lead"


class QuestionAnswer(BaseModel):
    answer: str


class QuestionAnswerTranslate(BaseModel):
    structured: str
    translator: str = "mgmt-lead"


class ReportSection(BaseModel):
    heading: str
    body: str = ""           # markdown / plain text per section
    bullets: list[str] = []  # optional bullet list
    metric: str | None = None  # optional headline metric for the section


class ReportIn(BaseModel):
    """Standardized report payload from the reporter agent.

    Two shapes are accepted so existing markdown reports keep working:
      • legacy: `content_md` (raw markdown body)
      • structured: `summary` + `sections[]` + optional `metrics`/`tags`

    A future PyPI consumer can feed the same JSON straight into a CLI
    report-renderer; the web viewer here is just one renderer of many.
    """
    title: str
    author: str = "reporter"
    # Legacy markdown body (still supported for back-compat)
    content_md: str = ""
    # Structured fields (preferred for new reports)
    summary: str = ""
    sections: list[ReportSection] = []
    metrics: dict = {}        # e.g. {"tokens": 12345, "cost_usd": 0.42}
    tags: list[str] = []
    severity: str = "info"    # info | success | warning | critical


class MissionIn(BaseModel):
    company: str = ""
    industry: str
    philosophy: str
    goal: str


class TeamConfirm(BaseModel):
    dev_agents: list[str]
    domain_agents: list[str]


class RequirementIn(BaseModel):
    text: str
    assigned_to: str | None = None
    # If true (or if env OMNI_AUTO_COORDINATE=1), the backend also spins
    # up a coordinator task to auto-play agent state transitions for
    # this requirement.
    auto_coordinate: bool | None = None


class RequirementStatus(BaseModel):
    status: Literal["new", "planning", "in_progress", "done", "cancelled"]


class BacklogIn(BaseModel):
    title: str
    team: str | None = None
    priority: str | None = None
    source_req_id: str | None = None


class BacklogStatus(BaseModel):
    status: Literal["next", "planning", "working", "done", "cancelled"]


class BacklogPatch(BaseModel):
    # id / created_at 제외 임의 필드 업데이트용.
    title: str | None = None
    team: str | None = None
    priority: str | None = None
    assignee: str | None = None
    source_req_id: str | None = None
    status: Literal["next", "planning", "working", "done", "cancelled"] | None = None


class KnowledgeIn(BaseModel):
    agent: str
    topic: str
    insight: str


class EvolutionIn(BaseModel):
    agent: str
    kind: Literal["new_agent", "feature", "refactor", "retire_agent"]
    title: str
    rationale: str
    payload: dict | None = None


class EvolutionDecision(BaseModel):
    decision: Literal["accepted", "rejected"]
    note: str = ""


# ── Helpers ──────────────────────────────────────────────────────────
def parse_frontmatter(text: str):
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text
    fm, body = parts[1], parts[2]
    meta: dict = {}
    for line in fm.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    if "tools" in meta:
        meta["tools"] = [t.strip() for t in meta["tools"].split(",") if t.strip()]
    return meta, body.strip()


def _slugify(name: str) -> str:
    import re
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9\-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "project"


def _unique_slug(base: str) -> str:
    s = _slugify(base)
    if not (PROJECTS_DIR / s).exists():
        return s
    n = 2
    while (PROJECTS_DIR / f"{s}-{n}").exists():
        n += 1
    return f"{s}-{n}"


def get_app_mode() -> str:
    try:
        return (APP_MODE_FILE.read_text(encoding="utf-8").strip() or "")
    except Exception:
        return ""


def set_app_mode(mode: str) -> None:
    APP_MODE_FILE.write_text(mode, encoding="utf-8")


def get_active_project() -> str:
    try:
        return (ACTIVE_PROJECT_FILE.read_text(encoding="utf-8").strip() or "")
    except Exception:
        return ""


def set_active_project(slug: str) -> None:
    ACTIVE_PROJECT_FILE.write_text(slug, encoding="utf-8")


def _project_dir(slug: str) -> Path:
    return PROJECTS_DIR / slug


def _project_mission_file(slug: str) -> Path:
    return _project_dir(slug) / "mission.json"


def _import_legacy_mission_once() -> None:
    """If a legacy mission.json exists at project root, and projects dir is
    empty, import it into a project so the existing user keeps their setup."""
    if not LEGACY_MISSION_FILE.exists():
        return
    existing = [p for p in PROJECTS_DIR.iterdir() if p.is_dir()]
    if existing:
        return
    try:
        data = json.loads(LEGACY_MISSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    for k, v in DEFAULT_MISSION.items():
        data.setdefault(k, v)
    company = (data.get("company") or "project").strip() or "project"
    slug = _slugify(company)
    d = _project_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    (_project_mission_file(slug)).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    set_active_project(slug)
    # In legacy form we default to custom mode
    if not get_app_mode():
        set_app_mode("custom")


_import_legacy_mission_once()


def list_projects() -> list[dict]:
    out = []
    for p in sorted(PROJECTS_DIR.iterdir()):
        if not p.is_dir():
            continue
        mf = p / "mission.json"
        if not mf.exists():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append({
            "slug": p.name,
            "company": data.get("company", ""),
            "industry": data.get("industry", ""),
            "goal": data.get("goal", ""),
            "team_confirmed": bool(data.get("team_confirmed")),
            "dev_count": len(data.get("dev_agents") or []),
            "domain_count": len(data.get("domain_agents") or []),
        })
    return out


def load_mission() -> dict:
    slug = get_active_project()
    mf = _project_mission_file(slug) if slug else None
    if mf and mf.exists():
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            for k, v in DEFAULT_MISSION.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(DEFAULT_MISSION)


def save_mission(m: dict) -> None:
    slug = get_active_project()
    if not slug:
        # No active project — fall back to a temp "scratch" project so we
        # never drop the data on the floor.
        slug = "scratch"
        d = _project_dir(slug)
        d.mkdir(parents=True, exist_ok=True)
        set_active_project(slug)
    mf = _project_mission_file(slug)
    mf.parent.mkdir(parents=True, exist_ok=True)
    mf.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


def current_roster() -> list[str]:
    """Return the list of agent names this project actually uses.

    Base roles are always included. Dev/domain agents come from the
    confirmed mission config; before confirmation we fall back to the
    union so the viewer isn't empty (and so real work can still flow
    through hooks during setup)."""
    mission = load_mission()
    if mission.get("team_confirmed"):
        dev = mission.get("dev_agents", [])
        domain = mission.get("domain_agents", [])
    else:
        dev = DEV_CATALOG
        domain = DOMAIN_CATALOG
    # LLM-proposed custom agents ride in their own lists — merge them in so
    # the topology shows the orchestrator's real team, not just catalog hits.
    custom_dev = [s.get("name") for s in mission.get("custom_dev_specs", []) if isinstance(s, dict) and s.get("name")]
    custom_domain = [s.get("name") for s in mission.get("custom_domain_specs", []) if isinstance(s, dict) and s.get("name")]
    roster = (
        list(BASE_ROLES.keys())
        + [n for n in dev if n in DEV_CATALOG]
        + [n for n in domain if n in DOMAIN_CATALOG]
        + custom_dev
        + custom_domain
    )
    return roster


def team_of(name: str) -> tuple[str, str]:
    if name in BASE_ROLES:
        return BASE_ROLES[name]
    if name in DEV_CATALOG:
        return ("dev", "#7cc7e8")
    if name in DOMAIN_CATALOG:
        return ("domain", "#ffd54f")
    # Custom specs from LLM proposal — look up in active mission to
    # resolve the team bucket.
    m = load_mission()
    for spec in m.get("custom_dev_specs", []) or []:
        if isinstance(spec, dict) and spec.get("name") == name:
            return ("dev", "#7cc7e8")
    for spec in m.get("custom_domain_specs", []) or []:
        if isinstance(spec, dict) and spec.get("name") == name:
            return ("domain", "#ffd54f")
    return ("misc", "#999999")


def load_agents() -> list[dict]:
    agents = []
    roster = set(current_roster())
    seen = set()
    for f in sorted(TEMPLATES.glob("*.md")):
        if f.stem.lower() == "readme":
            continue
        meta, body = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not meta or "name" not in meta:
            continue
        name = meta["name"]
        if name not in roster:
            continue
        team, color = team_of(name)
        meta.update({
            "team": team,
            "color": color,
            "body": body,
            "state": STATES.get(name, "idle"),
        })
        agents.append(meta)
        seen.add(name)
    # Merge LLM-proposed custom agents whose specs live inline in
    # mission.json — they don't have a template .md file on disk.
    mission = load_mission()
    for spec_list, team_key, color in [
        (mission.get("custom_dev_specs", []) or [], "dev", "#7cc7e8"),
        (mission.get("custom_domain_specs", []) or [], "domain", "#ffd54f"),
    ]:
        for spec in spec_list:
            if not isinstance(spec, dict):
                continue
            name = spec.get("name")
            if not name or name in seen:
                continue
            if name not in roster:
                continue
            tools = spec.get("tools") or ""
            tools_list = [t.strip() for t in tools.split(",") if t.strip()] if isinstance(tools, str) else list(tools or [])
            agents.append({
                "name": name,
                "description": spec.get("description") or "",
                "model": spec.get("model") or "sonnet",
                "tools": tools_list,
                "body": spec.get("body") or spec.get("description") or "",
                "team": team_key,
                "color": color,
                "state": STATES.get(name, "idle"),
                "custom": True,
            })
            seen.add(name)
    return agents


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def log_event(agent: str, kind: str, detail: str) -> dict:
    evt = {
        "id": str(uuid.uuid4())[:8],
        "ts": now_iso(),
        "agent": agent,
        "kind": kind,
        "detail": detail,
    }
    ACTIVITY.append(evt)
    _save_state()
    return evt


def _agent_model_attr(agent_name: str) -> str | None:
    try:
        f = TEMPLATES / f"{agent_name}.md"
        if not f.exists():
            return None
        meta, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        if meta and "model" in meta:
            return str(meta["model"]).strip().lower()
    except Exception:
        pass
    return None


def model_of(agent_name: str) -> str:
    attr = _agent_model_attr(agent_name)
    if attr:
        if "haiku" in attr: return "haiku"
        if "opus"  in attr: return "opus"
        if "sonnet" in attr: return "sonnet"
    team, _ = team_of(agent_name)
    return "opus" if team in ("top", "leads") else "sonnet"


def _tier_of(agent_name: str) -> int:
    team, _ = team_of(agent_name)
    if team == "top":   return 1
    if team == "leads": return 2
    return 3


def accrue_cost(agent_name: str, tokens_in: int, tokens_out: int) -> float:
    global COST_TOTAL
    model = model_of(agent_name)
    price = PRICING[model]
    delta = (tokens_in * price["in"] + tokens_out * price["out"]) / 1_000_000
    COST_TOTAL += delta
    COST_BY_MODEL[model] = COST_BY_MODEL.get(model, 0.0) + delta
    TOKENS_BY_MODEL[model]["in"]  += tokens_in
    TOKENS_BY_MODEL[model]["out"] += tokens_out
    # Per-agent cost / token ledger so the AgentPanel can show each
    # character's "salary" (= cumulative spend on this specific agent).
    bucket = COST_BY_AGENT.setdefault(agent_name, {"cost": 0.0, "in": 0, "out": 0, "calls": 0})
    bucket["cost"] += delta
    bucket["in"]   += tokens_in
    bucket["out"]  += tokens_out
    bucket["calls"] += 1
    return delta


def _accrue_for_state_working(agent_name: str) -> None:
    model = model_of(agent_name)
    if model == "haiku":
        tokens_in, tokens_out = 600, 300
    else:
        tier = _tier_of(agent_name)
        if tier == 1:
            tokens_in, tokens_out = 2500, 1500
        elif tier == 2:
            tokens_in, tokens_out = 1800, 1000
        else:
            tokens_in, tokens_out = (2000, 1000) if model == "opus" else (900, 450)
    accrue_cost(agent_name, tokens_in, tokens_out)


# ── FastAPI app ──────────────────────────────────────────────────────
app = FastAPI(title="OmniHarness Viewer", version="0.5.0")


@app.get("/api/topology")
def topology():
    agents = load_agents()
    # Only return teams that actually have members — post-slim there are
    # no silent placeholder rooms (mgmt/domain used to render empty).
    teams_out = []
    for t in TEAMS:
        members = [a["name"] for a in agents if a["team"] == t["id"]]
        if not members and t["id"] not in ("top", "dev", "eval"):
            continue  # hide empty non-core rooms (knowledge-only teams too)
        teams_out.append({**t, "members": members})
    # Knowledge reference docs — rendered as bookshelf items in the scene,
    # not as agents. Each slug maps to projects/<proj>/knowledge/<slug>.md.
    mission = load_mission()
    knowledge_slugs = (mission.get("knowledge") or []) if isinstance(mission, dict) else []
    knowledge = []
    for slug in knowledge_slugs:
        pretty = slug.replace("_", " ").title()
        knowledge.append({"slug": slug, "title_ko": pretty, "title_en": pretty})
    pending_q = sum(1 for q in QUESTIONS if q["status"] in ("pending_user",))
    pending_req = sum(1 for r in REQUIREMENTS if r["status"] not in ("done", "cancelled"))
    pending_evo = sum(1 for e in EVOLUTION if e["status"] == "proposed")
    return {
        "agents": agents,
        "teams": teams_out,
        "knowledge": knowledge,
        "total": len(agents),
        "cost_total": round(COST_TOTAL, 4),
        "cost_by_model": {k: round(v, 4) for k, v in COST_BY_MODEL.items()},
        "pending_questions": pending_q,
        "report_count": len(REPORTS),
        "activity_count": len(ACTIVITY),
        "pending_requirements": pending_req,
        "backlog_count": len(BACKLOG),
        "pending_evolution": pending_evo,
    }


@app.get("/api/states")
def states():
    return {"states": STATES}


@app.post("/api/agents/{name}/state")
def set_state(name: str, update: StateUpdate):
    roster = set(current_roster())
    if name not in roster:
        raise HTTPException(404, f"unknown agent: {name}")
    prev = STATES.get(name, "idle")
    STATES[name] = update.state
    if prev != update.state:
        log_event(name, "state", f"{prev} → {update.state}")
        if update.state == "working":
            _accrue_for_state_working(name)
    _save_state()
    return {"name": name, "state": update.state}


# ── Activity log ─────────────────────────────────────────────────────
@app.get("/api/activity")
def get_activity(limit: int = 80):
    items = list(ACTIVITY)
    items.reverse()
    return {"events": items[:limit], "total": len(ACTIVITY)}


@app.post("/api/activity")
def post_activity(ev: ActivityEvent):
    evt = log_event(ev.agent, ev.kind, ev.detail)
    if ev.kind == "tool" and _tier_of(ev.agent) == 3:
        accrue_cost(ev.agent, 150, 100)
    return evt


# ── Questions ────────────────────────────────────────────────────────
@app.get("/api/questions")
def list_questions():
    return {"questions": QUESTIONS}


@app.post("/api/questions")
def create_question(q: QuestionIn):
    roster = set(current_roster())
    if q.agent not in roster:
        raise HTTPException(404, f"unknown agent: {q.agent}")
    qid = str(uuid.uuid4())[:8]
    short = _next_short_q_id()
    # OMNI_TRANSLATE_PASSTHROUGH=1 (default): mgmt-lead 가 실제로
    # translator.simplify() 를 돌려서 raw 를 도메인 전문가 친화적으로
    # 풀어쓴 뒤 translated 에 넣고 pending_user 로 승격. 실패하면 raw
    # 를 그대로 넣고 activity 에 '번역 실패 — raw 사용' 을 남긴다.
    # OMNI_TRANSLATE_PASSTHROUGH=0 이면 2-hop 플로우 (외부 mgmt-lead
    # 프로세스가 /translate 를 직접 호출) 로 되돌린다.
    passthrough = os.environ.get("OMNI_TRANSLATE_PASSTHROUGH", "1") in ("1", "true", "True")
    translated: str | None = None
    translate_failed = False
    if passthrough:
        try:
            translated = _translator.simplify(q.raw, {"agent": q.agent})
            if not translated:
                translated = q.raw
        except Exception:
            translated = q.raw
            translate_failed = True
        status = "pending_user"
    else:
        status = "pending_translation"
    item = {
        "id": qid,
        "short_id": short,
        "agent": q.agent,
        "raw": q.raw,
        "translated": translated,
        "answer": None,
        "answer_structured": None,
        "context": q.context,
        "status": status,
        "created": now_iso(),
        "answered": None,
    }
    QUESTIONS.insert(0, item)
    log_event(q.agent, "question", f"질문 제기({short}): " + q.raw[:48])
    if passthrough:
        if translate_failed:
            log_event(
                "mgmt-lead",
                "question",
                f"mgmt-lead 번역 실패 — raw 사용({short})",
            )
        else:
            log_event(
                "mgmt-lead",
                "question",
                f"mgmt-lead 번역 완료({short}): " + (translated or "")[:48],
            )
    _save_state()
    return item


def _lookup_qid_by_short(short_id: str) -> str:
    """Resolve a short id (``Q003``) to the internal hash ``id``. 404s
    if no match — matches the shape other question endpoints return."""
    for q in QUESTIONS:
        if q.get("short_id") == short_id:
            return q["id"]
    raise HTTPException(404, f"no question with short_id {short_id}")


class QuestionAnswerByShort(BaseModel):
    """Convenience body for ``/by-short/{sid}/answer``. Accepts ``text``
    per the public spec; internally we hand it to the existing answer
    endpoint which expects ``answer``."""

    text: str


@app.post("/api/questions/by-short/{short_id}/answer")
def answer_question_by_short(short_id: str, body: QuestionAnswerByShort):
    qid = _lookup_qid_by_short(short_id)
    return answer_question(qid, QuestionAnswer(answer=body.text))


@app.post("/api/questions/by-short/{short_id}/translate")
def translate_question_by_short(short_id: str, body: QuestionTranslate):
    qid = _lookup_qid_by_short(short_id)
    return translate_question(qid, body)


@app.post("/api/questions/{qid}/translate")
def translate_question(qid: str, body: QuestionTranslate):
    for q in QUESTIONS:
        if q["id"] == qid:
            q["translated"] = body.translated
            q["status"] = "pending_user"
            log_event(body.translator, "question", f"질문 번역({qid}): " + body.translated[:48])
            return q
    raise HTTPException(404, "question not found")


@app.post("/api/questions/{qid}/answer")
def answer_question(qid: str, body: QuestionAnswer):
    for q in QUESTIONS:
        if q["id"] == qid:
            q["answer"] = body.answer
            q["status"] = "pending_answer_translation"
            q["answered"] = now_iso()
            log_event("user", "question", f"사용자 답변 수신({qid}) — mgmt-lead 변환 대기")
            return q
    raise HTTPException(404, "question not found")


@app.post("/api/questions/{qid}/answer/translate")
def translate_answer(qid: str, body: QuestionAnswerTranslate):
    for q in QUESTIONS:
        if q["id"] == qid:
            q["answer_structured"] = body.structured
            q["status"] = "answered"
            log_event(
                body.translator,
                "question",
                f"답변 구조화({qid}) → {q['agent']}: " + body.structured[:48],
            )
            return q
    raise HTTPException(404, "question not found")


# ── Reports ──────────────────────────────────────────────────────────
@app.get("/api/reports")
def list_reports():
    summary = [{k: r[k] for k in ("id", "title", "author", "created")} for r in REPORTS]
    return {"reports": summary}


@app.get("/api/reports/{rid}")
def get_report(rid: str):
    for r in REPORTS:
        if r["id"] == rid:
            return r
    raise HTTPException(404, "report not found")


@app.delete("/api/reports/{rid}")
def delete_report(rid: str):
    """Remove a report from REPORTS. Used by the audit-dedup cleanup
    flow when two runs produced near-identical digests and the user
    wants the older one gone. Kept simple: no admin guard (viewer is
    localhost-only) and no soft-delete — the record is dropped and the
    state file rewritten so the next boot agrees with the live viewer.
    """
    for i, r in enumerate(REPORTS):
        if r.get("id") == rid:
            removed = REPORTS.pop(i)
            log_event("user", "report", f"보고서 삭제: {removed.get('title', rid)}")
            _save_state()
            return {"ok": True, "id": rid, "title": removed.get("title")}
    raise HTTPException(404, "report not found")


@app.post("/api/reports")
def create_report(r: ReportIn):
    rid = str(uuid.uuid4())[:8]
    # If the caller only provided `content_md`, derive a synthetic
    # summary so the structured renderer still has something to show.
    summary = r.summary or (r.content_md or "").splitlines()[0:1]
    if isinstance(summary, list):
        summary = (summary[0] if summary else "").lstrip("# ").strip()
    item = {
        "id": rid,
        "title": r.title,
        "author": r.author,
        "created": now_iso(),
        "severity": r.severity or "info",
        "tags": list(r.tags or []),
        "summary": summary,
        "sections": [s.model_dump() for s in (r.sections or [])],
        "metrics": dict(r.metrics or {}),
        # keep markdown body around for backward-compat readers / PyPI CLI
        "content_md": r.content_md or "",
    }
    REPORTS.insert(0, item)
    # Persist the structured JSON to disk so the same payload can be
    # streamed to a future PyPI CLI / static-site builder.
    fn_json = REPORTS_DIR / f"{item['created'].replace(':','-')}-{rid}.json"
    fn_json.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    if r.content_md:
        fn_md = REPORTS_DIR / f"{item['created'].replace(':','-')}-{rid}.md"
        fn_md.write_text(
            f"# {r.title}\n\n_by {r.author} @ {item['created']}_\n\n{r.content_md}",
            encoding="utf-8",
        )
    log_event(r.author, "report", f"보고서 발행: {r.title}")
    return item


# ── Mission ─────────────────────────────────────────────────────────
@app.get("/api/mission")
def get_mission():
    return load_mission()


@app.post("/api/mission")
def set_mission(m: MissionIn):
    company = (m.company or "").strip()
    industry = m.industry.strip()
    philosophy = m.philosophy.strip()
    goal = m.goal.strip()
    existing = load_mission()
    data = {
        **existing,
        "company": company,
        "industry": industry,
        "philosophy": philosophy,
        "goal": goal,
        "placeholder": not (company and industry and goal),
    }
    save_mission(data)
    log_event("system", "mission", f"사훈 설정: {company} · {industry}")
    return data


def _propose_team(mission: dict) -> tuple[list[str], list[str], str]:
    """Fixed-shape roster proposal (slimmed 2026-04-19).

    Every project gets the same 8-agent roster now — orchestrator +
    dev-lead + 6 reviewers. Feature-specific dev-* fan-out and domain
    specialists are gone; feature work is tagged on dev-lead's activity
    stream, and domain rules live as markdown under `projects/<proj>/
    knowledge/*.md`. Industry keywords still drive the initial knowledge
    seeding (e.g. a fab project gets 4 canonical knowledge docs)."""
    industry = (mission.get("industry") or "").lower()
    goal = (mission.get("goal") or "").lower()
    blob = f"{industry} {goal}"

    dev: list[str] = ["dev-lead"]
    domain: list[str] = []  # no domain agents anymore — see knowledge/
    if any(k in blob for k in ["semicon", "fab", "반도체", "wafer", "yield", "수율"]):
        reason = (
            "반도체/수율 도메인 감지 → dev-lead 1 + 리뷰어 6 + knowledge 4 "
            "(process_area / causal_direction / dvc_parameter / adapter_mapping)"
        )
    elif any(k in blob for k in ["commerce", "shop", "쇼핑", "retail", "order"]):
        reason = "이커머스 도메인 감지 → dev-lead + 리뷰어 6 (knowledge 는 프로젝트별 추가)"
    elif any(k in blob for k in ["data", "analytics", "분석", "ml", "ai", "model"]):
        reason = "데이터/분석 도메인 감지 → dev-lead + 리뷰어 6 (knowledge 는 프로젝트별 추가)"
    else:
        reason = "범용 웹 프로젝트 → dev-lead + 리뷰어 6 (knowledge 는 프로젝트별 추가)"
    return dev, domain, reason


@app.post("/api/mission/propose_team")
def propose_team():
    mission = load_mission()
    if mission.get("placeholder"):
        raise HTTPException(400, "mission must be set first")
    # Prefer LLM-driven proposal when an API provider is wired up.
    # Heuristic is only the fallback — it's catalog-locked and can't
    # invent project-specific agent names.
    provider = _detect_provider()
    llm_result = None
    if provider in ("anthropic", "bedrock", "openai", "gemini"):
        try:
            llm_result = _propose_team_via_llm(mission, provider)
        except Exception as e:
            log_event("orchestrator", "error", f"LLM 팀 제안 실패, 휴리스틱으로 폴백: {e}")
            llm_result = None

    if llm_result is not None:
        dev_specs, domain_specs, reason = llm_result
        # Names-only arrays keep backward compatibility with existing
        # wizard/roster logic; the full specs ride in custom_*_specs so
        # load_agents() can merge them into topology.
        mission["proposed_dev_agents"] = [s["name"] for s in dev_specs]
        mission["proposed_domain_agents"] = [s["name"] for s in domain_specs]
        mission["proposed_custom_dev_specs"] = dev_specs
        mission["proposed_custom_domain_specs"] = domain_specs
        mission["proposal_reason"] = reason
        mission["proposal_source"] = provider
    else:
        dev, domain, reason = _propose_team(mission)
        mission["proposed_dev_agents"] = dev
        mission["proposed_domain_agents"] = domain
        mission["proposed_custom_dev_specs"] = []
        mission["proposed_custom_domain_specs"] = []
        mission["proposal_reason"] = reason
        mission["proposal_source"] = "heuristic"

    save_mission(mission)
    log_event("orchestrator", "team",
              f"팀 구성 제안 [{mission['proposal_source']}] — dev {len(mission['proposed_dev_agents'])} · domain {len(mission['proposed_domain_agents'])}")
    return mission


def _propose_team_via_llm(mission: dict, provider: str):
    """Ask Claude to design a project-specific team. Returns
    (dev_specs, domain_specs, reason). Each spec is a dict with
    {name, description, model, tools}."""
    import json as _json
    import re as _re

    system = (
        "You are the orchestrator of an agent team for a Claude Code project. "
        "Your job here is to propose the most useful DEV and DOMAIN agents for "
        "the project described below. Think carefully about what roles the "
        "project actually needs — not what some generic template would pick. "
        "Do NOT over-propose. 3–6 dev agents is usually the right range.\n\n"
        "BASE TEAM is fixed and always present (do NOT repeat): orchestrator, "
        "dev-lead, mgmt-lead, eval-lead, reporter, hr, auditor, ux-reviewer, "
        "dev-verifier, user-role-tester, admin-role-tester, security-auditor, "
        "domain-researcher.\n\n"
        "Your additions fill the gaps between the base team and what this "
        "project specifically needs."
    )
    user = (
        f"Project:\n"
        f"- Company: {mission.get('company') or '—'}\n"
        f"- Industry: {mission.get('industry') or '—'}\n"
        f"- Philosophy: {mission.get('philosophy') or '—'}\n"
        f"- Goal: {mission.get('goal') or '—'}\n\n"
        "Respond with ONLY a JSON object — no prose, no markdown fences — in "
        "this exact shape:\n"
        "{\n"
        '  "dev_agents": [\n'
        '    {"name": "dev-<kebab-case>", "description": "1-2 sentences in user language", "model": "sonnet"|"opus", "tools": "Read, Write, Edit, Bash, Grep, Glob"}\n'
        "  ],\n"
        '  "domain_agents": [\n'
        '    {"name": "<kebab-case>", "description": "1-2 sentences", "model": "sonnet"|"opus", "tools": "Read, Grep, Glob"}\n'
        "  ],\n"
        '  "reason": "One sentence explaining why this team fits the project"\n'
        "}\n\n"
        "Rules:\n"
        "- dev agent names MUST start with `dev-` (kebab-case after).\n"
        "- domain agent names are kebab-case without prefix.\n"
        "- Use Opus only for agents that need deep reasoning; default to Sonnet.\n"
        "- Write description in the same language as the project goal.\n"
        "- No trailing commas, no comments."
    )

    text = _llm_oneshot(system, user, provider)
    # Strip any markdown fencing the model might still add.
    m = _re.search(r"\{.*\}", text, _re.DOTALL)
    if not m:
        raise RuntimeError(f"no JSON object in LLM response: {text[:200]}")
    payload = _json.loads(m.group(0))

    def _clean_specs(raw, is_dev):
        out = []
        for spec in (raw or []):
            if not isinstance(spec, dict):
                continue
            name = (spec.get("name") or "").strip()
            if not name:
                continue
            # Enforce naming convention so topology team-bucket is correct.
            if is_dev and not name.startswith("dev-"):
                name = "dev-" + name.lstrip("-")
            model = (spec.get("model") or "sonnet").lower()
            if model not in ("sonnet", "opus", "haiku"):
                model = "sonnet"
            out.append({
                "name": name,
                "description": (spec.get("description") or "").strip(),
                "model": model,
                "tools": (spec.get("tools") or "Read, Write, Edit, Bash, Grep, Glob").strip(),
                "team": "dev" if is_dev else "domain",
                "custom": True,
            })
        return out

    dev_specs = _clean_specs(payload.get("dev_agents"), True)
    domain_specs = _clean_specs(payload.get("domain_agents"), False)
    reason = (payload.get("reason") or "").strip() or "LLM-generated team proposal."
    return dev_specs, domain_specs, reason


def _llm_oneshot(system: str, user: str, provider: str) -> str:
    """Single-turn call. Tries ``provider`` first, then walks through the
    rest via ``translator._llm_call`` so multi-provider fallback is unified.

    Team-proposal needs ~2000 tokens and a stronger model than translator,
    so we handle Anthropic/Bedrock inline (with ANTHROPIC_MODEL overrides).
    For OpenAI/Gemini we delegate to ``translator._llm_call``, which walks
    the same provider priority and handles optional imports cleanly.
    """
    if provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic()
        model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = []
        for blk in resp.content:
            if getattr(blk, "type", None) == "text":
                parts.append(blk.text)
        return "\n".join(parts)
    if provider == "bedrock":
        import boto3
        region = os.environ.get("AWS_REGION", "us-east-1")
        model = os.environ.get("ANTHROPIC_MODEL", "anthropic.claude-opus-4-7-v1:0")
        client = boto3.client("bedrock-runtime", region_name=region)
        resp = client.converse(
            modelId=model,
            messages=[{"role": "user", "content": [{"text": user}]}],
            system=[{"text": system}],
            inferenceConfig={"maxTokens": 2000},
        )
        out = resp.get("output", {}).get("message", {})
        parts = [c.get("text", "") for c in out.get("content", []) if c.get("text")]
        return "\n".join(parts)
    if provider in ("openai", "gemini"):
        # Delegate to the unified translator dispatch — it walks providers
        # in priority order and handles optional imports. Anthropic/Bedrock
        # are already filtered out above, so this reliably lands on the
        # openai/gemini branch when those keys are the only ones present.
        from translator import _llm_call as _t_llm_call  # type: ignore
        out = _t_llm_call(system, user)
        if out:
            return out
        raise RuntimeError(f"LLM provider '{provider}' produced no output")
    raise RuntimeError(f"no LLM provider available ({provider})")


@app.post("/api/mission/confirm_team")
def confirm_team(body: TeamConfirm):
    mission = load_mission()
    dev_catalog_agents = [x for x in body.dev_agents if x in DEV_CATALOG]
    domain_catalog_agents = [x for x in body.domain_agents if x in DOMAIN_CATALOG]

    # Carry over LLM-proposed custom specs for names the user kept.
    kept_dev_names = set(body.dev_agents)
    kept_domain_names = set(body.domain_agents)
    proposed_dev_specs = mission.get("proposed_custom_dev_specs", []) or []
    proposed_domain_specs = mission.get("proposed_custom_domain_specs", []) or []
    custom_dev_specs = [
        s for s in proposed_dev_specs
        if isinstance(s, dict) and s.get("name") in kept_dev_names
    ]
    custom_domain_specs = [
        s for s in proposed_domain_specs
        if isinstance(s, dict) and s.get("name") in kept_domain_names
    ]

    mission["dev_agents"] = dev_catalog_agents
    mission["domain_agents"] = domain_catalog_agents
    mission["custom_dev_specs"] = custom_dev_specs
    mission["custom_domain_specs"] = custom_domain_specs
    mission["team_confirmed"] = True
    save_mission(mission)
    total = len(dev_catalog_agents) + len(custom_dev_specs) + len(domain_catalog_agents) + len(custom_domain_specs)
    log_event("orchestrator", "team",
              f"팀 구성 확정 — dev {len(dev_catalog_agents)}+{len(custom_dev_specs)} custom · domain {len(domain_catalog_agents)}+{len(custom_domain_specs)} custom · 총 {total}")
    return mission


# ── App mode (general | custom) ─────────────────────────────────────
class AppModeIn(BaseModel):
    mode: Literal["general", "custom", ""]


@app.get("/api/mode")
def api_get_mode():
    return {"mode": get_app_mode()}


@app.post("/api/mode")
def api_set_mode(body: AppModeIn):
    set_app_mode(body.mode)
    if body.mode:
        log_event("system", "mode", f"앱 모드 전환: {body.mode}")
    else:
        log_event("system", "mode", "모드 선택 화면으로 복귀")
    return {"mode": body.mode}


# ── Projects ────────────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    company: str
    industry: str = ""
    philosophy: str = ""
    goal: str = ""


@app.get("/api/projects")
def api_list_projects():
    return {"projects": list_projects(), "active": get_active_project()}


@app.post("/api/projects")
def api_create_project(p: ProjectCreate):
    name = (p.company or "").strip()
    if not name:
        raise HTTPException(400, "company is required")
    slug = _unique_slug(name)
    d = _project_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    data = {
        **DEFAULT_MISSION,
        "company": name,
        "industry": (p.industry or "").strip(),
        "philosophy": (p.philosophy or "").strip(),
        "goal": (p.goal or "").strip(),
        "placeholder": not ((p.industry or "").strip() and (p.goal or "").strip()),
    }
    _project_mission_file(slug).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    set_active_project(slug)
    log_event("system", "project", f"프로젝트 생성: {name} ({slug})")
    return {"slug": slug, **data}


@app.post("/api/projects/{slug}/activate")
def api_activate_project(slug: str):
    d = _project_dir(slug)
    if not d.exists():
        raise HTTPException(404, "project not found")
    set_active_project(slug)
    # Reset in-memory working state so a fresh project starts clean
    STATES.clear()
    log_event("system", "project", f"프로젝트 전환: {slug}")
    return {"active": slug}


@app.delete("/api/projects/{slug}")
def api_delete_project(slug: str):
    d = _project_dir(slug)
    if not d.exists():
        raise HTTPException(404, "project not found")
    import shutil
    shutil.rmtree(d)
    if get_active_project() == slug:
        set_active_project("")
    log_event("system", "project", f"프로젝트 삭제: {slug}")
    return {"ok": True}


@app.get("/api/mission/catalog")
def team_catalog():
    """Return the dev/domain catalog with display metadata so the UI can
    show a selectable list during onboarding."""
    return {
        "dev": [{"name": n} for n in DEV_CATALOG],
        "domain": [{"name": n} for n in DOMAIN_CATALOG],
    }


@app.get("/api/guide/bedrock")
def get_bedrock_guide():
    # IAM 정책 스니펫 — copy-pastable. `bedrock:InvokeModel` +
    # `bedrock:InvokeModelWithResponseStream` 만 최소 권한으로 묶는다.
    iam_policy = (
        "{\n"
        '  "Version": "2012-10-17",\n'
        '  "Statement": [{\n'
        '    "Effect": "Allow",\n'
        '    "Action": [\n'
        '      "bedrock:InvokeModel",\n'
        '      "bedrock:InvokeModelWithResponseStream"\n'
        "    ],\n"
        '    "Resource": [\n'
        '      "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"\n'
        "    ]\n"
        "  }]\n"
        "}"
    )
    win_setx_body = (
        "cmd.exe 에서 영구 저장 (setx — 현재 창에는 적용 안 됨, 새 창부터):\n\n"
        "```\n"
        "setx CLAUDE_CODE_USE_BEDROCK 1\n"
        "setx AWS_ACCESS_KEY_ID AKIA...\n"
        "setx AWS_SECRET_ACCESS_KEY wJalrXUtn...\n"
        "setx AWS_REGION us-east-1\n"
        "setx ANTHROPIC_MODEL anthropic.claude-opus-4-7-v1:0\n"
        "setx ANTHROPIC_SMALL_FAST_MODEL anthropic.claude-haiku-4-5-20251001-v1:0\n"
        "```\n\n"
        "PowerShell 에서 현재 세션만:\n\n"
        "```\n"
        "$env:CLAUDE_CODE_USE_BEDROCK = '1'\n"
        "$env:AWS_ACCESS_KEY_ID = 'AKIA...'\n"
        "$env:AWS_SECRET_ACCESS_KEY = 'wJalrXUtn...'\n"
        "$env:AWS_REGION = 'us-east-1'\n"
        "$env:ANTHROPIC_MODEL = 'anthropic.claude-opus-4-7-v1:0'\n"
        "```\n\n"
        "OmniHarness 웹 UI 에서 입력한 값은 이미 프로세스 환경에 주입돼 있으니 "
        "서버 재시작 없이 바로 동작합니다 — `setx` 는 **다른 터미널/프로그램**에서도 "
        "같은 자격증명을 쓰고 싶을 때만."
    )
    win_setx_body_en = (
        "Persistent on Windows (setx — opens a NEW shell to see them):\n\n"
        "```\n"
        "setx CLAUDE_CODE_USE_BEDROCK 1\n"
        "setx AWS_ACCESS_KEY_ID AKIA...\n"
        "setx AWS_SECRET_ACCESS_KEY wJalrXUtn...\n"
        "setx AWS_REGION us-east-1\n"
        "setx ANTHROPIC_MODEL anthropic.claude-opus-4-7-v1:0\n"
        "setx ANTHROPIC_SMALL_FAST_MODEL anthropic.claude-haiku-4-5-20251001-v1:0\n"
        "```\n\n"
        "PowerShell for the current session only:\n\n"
        "```\n"
        "$env:CLAUDE_CODE_USE_BEDROCK = '1'\n"
        "$env:AWS_ACCESS_KEY_ID = 'AKIA...'\n"
        "$env:AWS_SECRET_ACCESS_KEY = 'wJalrXUtn...'\n"
        "$env:AWS_REGION = 'us-east-1'\n"
        "$env:ANTHROPIC_MODEL = 'anthropic.claude-opus-4-7-v1:0'\n"
        "```\n\n"
        "Values entered in the OmniHarness web UI are already injected into the "
        "running process — use `setx` only if you want the same creds in other "
        "terminals/programs."
    )
    return {
        "title_ko": "Amazon Bedrock 으로 Claude Code CLI 운영",
        "title_en": "Run Claude Code CLI on Amazon Bedrock",
        "sections_ko": [
            {"h": "왜 Bedrock?",
             "body": "사내 AWS 계정이 이미 있다면, 별도 Anthropic 계약 없이 회사 결제/감사 체계 안에서 Claude 모델을 쓸 수 있습니다. 데이터가 AWS 경계 안에 머무르고, IAM 으로 접근 통제가 됩니다."},
            {"h": "1. 모델 접근 승인",
             "body": "AWS 콘솔 → Bedrock → 왼쪽 `Model access` → `Manage model access` → Anthropic 모델 (Claude 4.x Opus/Sonnet/Haiku) 체크 후 Submit. 승인까지 몇 분~수 시간."},
            {"h": "2. IAM 정책 (최소 권한)",
             "body": "해당 IAM 유저/역할에 다음 정책을 attach 합니다:\n\n```\n" + iam_policy + "\n```"},
            {"h": "3. Windows 환경변수 (setx / PowerShell)",
             "body": win_setx_body},
            {"h": "4. 쉘 (macOS / Linux) 환경변수",
             "body": "쉘 rc 파일(.zshrc / .bashrc) 에 추가:\n\n```\nexport CLAUDE_CODE_USE_BEDROCK=1\nexport AWS_REGION=us-east-1\nexport ANTHROPIC_MODEL=anthropic.claude-opus-4-7-v1:0\nexport ANTHROPIC_SMALL_FAST_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0\n```"},
            {"h": "5. OmniHarness 에 연결 (가장 빠른 길)",
             "body": "HUD 의 🔑 키 패널에서 **AWS Access Key / Secret / Region** 입력 → **Bedrock 사용** 체크 → **🔌 연결 테스트** 클릭. 성공하면 바로 Requirements 입력 시 Bedrock Claude 가 orchestrator 로 응답합니다. `setx` 없이도 OmniHarness 프로세스가 살아있는 동안은 OK."},
            {"h": "6. 검증",
             "body": "`aws bedrock list-foundation-models --region us-east-1` 로 모델 목록이 보이는지 먼저 확인. 그 다음 OmniHarness 🔑 키 패널의 🔌 연결 테스트 버튼 → 한국어 힌트로 에러 원인 진단."},
        ],
        "sections_en": [
            {"h": "Why Bedrock?",
             "body": "If you already have an AWS account, you can use Claude models through your existing billing/audit boundary without a separate Anthropic contract. Data stays inside AWS; IAM controls access."},
            {"h": "1. Request model access",
             "body": "AWS Console → Bedrock → `Model access` → `Manage model access` → check Anthropic models (Claude 4.x Opus/Sonnet/Haiku) → Submit. Approval takes minutes to hours."},
            {"h": "2. IAM policy (least privilege)",
             "body": "Attach this policy to the IAM user/role:\n\n```\n" + iam_policy + "\n```"},
            {"h": "3. Windows env vars (setx / PowerShell)",
             "body": win_setx_body_en},
            {"h": "4. Shell env vars (macOS / Linux)",
             "body": "Add to shell rc:\n\n```\nexport CLAUDE_CODE_USE_BEDROCK=1\nexport AWS_REGION=us-east-1\nexport ANTHROPIC_MODEL=anthropic.claude-opus-4-7-v1:0\nexport ANTHROPIC_SMALL_FAST_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0\n```"},
            {"h": "5. Fastest path via OmniHarness",
             "body": "In the 🔑 keys panel: enter **AWS Access Key / Secret / Region** → check **Use Bedrock** → click **🔌 Test connection**. On success, Requirements immediately route through Bedrock Claude as orchestrator. No `setx` needed while the OmniHarness process is alive."},
            {"h": "6. Verification",
             "body": "Run `aws bedrock list-foundation-models --region us-east-1` to confirm the models show up. Then use the 🔌 Test connection button in the 🔑 keys panel — errors come back with Korean hints pointing to the usual causes."},
        ],
    }


# ── Requirements ────────────────────────────────────────────────────
@app.get("/api/requirements")
def list_requirements():
    return {"requirements": list(REQUIREMENTS)}


@app.post("/api/requirements")
async def create_requirement(r: RequirementIn):
    rid = str(uuid.uuid4())[:8]
    item = {
        "id": rid,
        "text": r.text,
        "created": now_iso(),
        "status": "new",
        "from": "user",
        "assigned_to": r.assigned_to or "orchestrator",
    }
    REQUIREMENTS.insert(0, item)
    log_event("orchestrator", "requirement", "🎯 사용자 요구사항 수신: " + r.text[:120])
    # 요구사항 → 자동 백로그 시딩
    bid = str(uuid.uuid4())[:8]
    backlog_item = {
        "id": bid,
        "title": (r.text or "")[:60],
        "team": r.assigned_to or "orchestrator",
        "priority": "high",
        "status": "next",
        "source_req_id": rid,
        "created_at": now_iso(),
    }
    BACKLOG.insert(0, backlog_item)
    _save_state()
    # ── Optional auto-coordination ───────────────────────────────────
    # If OMNI_AUTO_COORDINATE=1 in env, or the request body opts in,
    # kick off the coordinator task in the background. We swallow
    # failures here — creating the requirement must succeed even if
    # the coordinator can't start (e.g. no running event loop).
    auto = bool(r.auto_coordinate) or os.environ.get("OMNI_AUTO_COORDINATE") in ("1", "true", "True")
    if auto:
        try:
            _coordinator.start_coordinator(rid)
        except Exception as e:
            log_event("orchestrator", "coord", f"coordinator 자동시작 실패: {e}")

    # ── Orchestrator agentic seed (Bedrock / Anthropic / …) ─────────
    # When a provider is configured, the orchestrator drafts an initial
    # Report + up to 3 plain-Korean Questions + feature tags in the
    # background. This is what makes "Requirements 입력 → 바로 Claude
    # Code 같은 자연스러움" work: the user writes a requirement and the
    # orchestrator immediately starts doing something visible, instead
    # of waiting for Claude Code CLI hooks. Falls back silently to no-op
    # when no LLM key is set (STUB mode). Env opt-out with
    # ``OMNI_ORCHESTRATOR_SEED=0``.
    seed_enabled = os.environ.get("OMNI_ORCHESTRATOR_SEED", "1") in ("1", "true", "True")
    if seed_enabled:
        provider = _detect_provider()
        if provider in ("anthropic", "bedrock", "openai", "gemini"):
            try:
                asyncio.create_task(_run_orchestrator_seed(rid, r.text, provider))
            except Exception as e:
                log_event("orchestrator", "seed", f"seed 자동시작 실패: {e}")
    return item


async def _run_orchestrator_seed(rid: str, text: str, provider: str) -> None:
    """Background — ask the configured LLM (usually Bedrock Claude) to
    draft an orchestrator-level response to a fresh requirement. We
    light up the orchestrator agent as ``working`` during the call so
    the viewer reflects real activity, then drop back to ``idle`` once
    the Questions + Report are seeded.

    Output shape (JSON): {summary, feature_tags[], questions[], report_md}.
    Malformed JSON is swallowed — the seed is best-effort, not required.
    """
    _set_state_safe("orchestrator", "working")
    log_event("orchestrator", "seed", f"요구사항 초안 작성 시작 ({provider})")
    try:
        mission = load_mission()
        knowledge_slugs = (mission.get("knowledge") or []) if isinstance(mission, dict) else []
        system = (
            "당신은 OmniHarness 의 orchestrator 입니다. 사용자가 방금 올린 FabCanvas 요구사항을 받고, "
            "단일 턴으로 다음 JSON 스키마에 맞는 초안을 작성하세요. 반드시 파싱 가능한 JSON 만 출력, "
            "설명 문장 금지.\n"
            "{\n"
            '  "summary": "2~3문장 요약 (평어체, 기술용어 최소)",\n'
            '  "feature_tags": ["dashboard"|"spc"|"ml"|"wafer-map"|"tablemap"|"ettime"|"tracker"|"filebrowser"|"admin"|"messages" … 0~3개],\n'
            '  "questions": ["사용자에게 물어야 할 불확실한 점 (평어체)", ...최대 3개],\n'
            '  "report_md": "# 초안\\n\\n평어체 마크다운으로 된 초기 계획·접근 방식"\n'
            "}\n"
            f"\n프로젝트: {mission.get('company', '')} · {mission.get('industry', '')}\n"
            f"목표: {mission.get('goal', '')}\n"
            f"참조 가능한 knowledge 문서: {', '.join(knowledge_slugs) or '(없음)'}\n"
            "리뷰어로는 dev-verifier · security-auditor · ux-reviewer · user-role-tester · "
            "admin-role-tester · domain-researcher 가 on-demand 로 존재. 구현은 dev-lead 단일 에이전트."
        )
        user = f"요구사항: {text.strip()[:2000]}"
        # _llm_oneshot is sync — push it to a thread so we don't block
        # the event loop while the Bedrock call takes a few seconds.
        raw = await asyncio.to_thread(_llm_oneshot, system, user, provider)
        payload = _parse_seed_json(raw)
        if not payload:
            log_event("orchestrator", "seed", "⚠️ 초안 JSON 파싱 실패 — skip")
            return

        # 1) Questions seed — plain Korean, straight to pending_user
        #    (skip the translator hop since orchestrator wrote these itself)
        for q_text in (payload.get("questions") or [])[:3]:
            q_text = str(q_text or "").strip()
            if not q_text:
                continue
            qid = str(uuid.uuid4())[:8]
            short = _next_short_q_id()
            QUESTIONS.insert(0, {
                "id": qid,
                "short_id": short,
                "agent": "orchestrator",
                "raw": q_text,
                "translated": q_text,
                "status": "pending_user",
                "created": now_iso(),
                "source_req_id": rid,
            })
            log_event("orchestrator", "question", f"질문 생성 ({short}): {q_text[:60]}")

        # 2) Report draft seed — orchestrator-authored, plain Korean.
        summary = (payload.get("summary") or "").strip()
        report_md = (payload.get("report_md") or "").strip() or f"# 요구사항 초안\n\n{summary or text[:200]}"
        report = {
            "id": str(uuid.uuid4())[:8],
            "title": f"🎯 요구사항 초안 — {text[:40]}",
            "author": "orchestrator",
            "severity": "info",
            "summary": summary or None,
            "content_md": report_md,
            "tags": payload.get("feature_tags") or [],
            "source_req_id": rid,
            "created": now_iso(),
        }
        REPORTS.insert(0, report)
        log_event("orchestrator", "report", f"초안 리포트 발행: {report['title'][:60]}")

        # 3) Tag the backlog item with feature tags for viewer grouping
        tags = payload.get("feature_tags") or []
        if tags:
            for b in BACKLOG:
                if b.get("source_req_id") == rid:
                    b["feature_tags"] = tags
                    break
        _save_state()
    except Exception as e:
        log_event("orchestrator", "seed", f"초안 실패: {e}")
    finally:
        _set_state_safe("orchestrator", "idle")
        log_event("orchestrator", "seed", "요구사항 초안 작업 종료")


def _set_state_safe(name: str, state: str) -> None:
    """In-process state flip + activity event. Safe when agent isn't in
    the roster — we just log and skip."""
    if name not in set(current_roster()):
        return
    prev = STATES.get(name, "idle")
    if prev == state:
        return
    STATES[name] = state
    log_event(name, "state", f"{prev} → {state}")
    if state == "working":
        _accrue_for_state_working(name)


def _parse_seed_json(raw: str | None) -> dict | None:
    """Pull the first JSON object out of the LLM response. Models often
    wrap structured output in prose or markdown fences, so we substring
    from the first ``{`` to the matching ``}`` before json.loads."""
    if not raw:
        return None
    s = raw.strip()
    # strip markdown fences
    if s.startswith("```"):
        s = s.split("```", 2)[-1].strip()
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(s[start:end + 1])
    except Exception:
        return None


@app.post("/api/coordinate/{rid}/start")
def coordinate_start(rid: str):
    """Manually start the coordinator for an existing requirement."""
    for item in REQUIREMENTS:
        if item["id"] == rid:
            try:
                ok = _coordinator.start_coordinator(rid)
            except Exception as e:
                raise HTTPException(500, f"failed to start: {e}")
            if not ok:
                raise HTTPException(409, "coordinator already running for this rid")
            return {"rid": rid, "started": True}
    raise HTTPException(404, "requirement not found")


@app.post("/api/coordinate/{rid}/stop")
def coordinate_stop(rid: str):
    ok = _coordinator.stop_coordinator(rid)
    if not ok:
        raise HTTPException(404, "no coordinator running for this rid")
    return {"rid": rid, "stopped": True}


@app.get("/api/coordinate")
def coordinate_list():
    return {"running": _coordinator.list_coordinators()}


# ── Coordinator completion hook + periodic audit trigger ────────────
def on_coordinator_complete(rid: str) -> None:
    """Called from coordinator.run_coordinator when a run reaches
    status=done (success path — cancel/failure paths skip this).

    Bumps COORDINATOR_COMPLETED and, every ``OMNI_AUDIT_EVERY`` runs,
    schedules an async audit pass on the main loop.
    """
    global COORDINATOR_COMPLETED
    COORDINATOR_COMPLETED += 1
    try:
        every = max(1, int(os.environ.get("OMNI_AUDIT_EVERY", "15")))
    except Exception:
        every = 5
    try:
        big_every = max(1, int(os.environ.get("SECURITY_AUDIT_EVERY", "10")))
    except Exception:
        big_every = 10

    audit_due = (COORDINATOR_COMPLETED % every == 0)
    big_sec_due = (COORDINATOR_COMPLETED % big_every == 0)
    if not audit_due and not big_sec_due:
        return

    # Schedule async on the main loop; swallow errors so the coordinator
    # doesn't crash on audit-side bugs. The two passes are independent —
    # big-picture security is a separate track from the general audit.
    loop = getattr(_coordinator, "_MAIN_LOOP", None)
    try:
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        def _schedule(coro_factory, sync_fallback) -> None:
            if loop is None:
                sync_fallback()
                return
            if running is loop:
                loop.create_task(coro_factory())
            else:
                asyncio.run_coroutine_threadsafe(coro_factory(), loop)

        if audit_due:
            _schedule(_audit.run_audit_pass_async, _audit.run_audit_pass)
        if big_sec_due:
            _schedule(
                _audit.run_big_security_pass_async,
                _audit.run_big_security_pass,
            )
    except Exception as e:
        log_event("hr", "audit", f"감사 스케줄링 실패: {e}")


# ── Audit endpoints (수동 트리거 + 상태 조회) ──────────────────────
@app.post("/api/audit/run")
def api_audit_run():
    """Manually trigger an audit pass synchronously. Returns the list of
    newly-created EVOLUTION proposal ids."""
    try:
        created = _audit.run_audit_pass()
    except Exception as e:
        raise HTTPException(500, f"audit failed: {e}")
    return {
        "created_ids": [c["id"] for c in created],
        "count": len(created),
        "items": created,
    }


@app.get("/api/audit/status")
def api_audit_status():
    return _audit.status()


@app.post("/api/audit/security/run")
def api_audit_security_run():
    """Manually trigger a big-picture security pass synchronously.
    Returns the newly-created EVOLUTION proposal ids tagged
    ``source='security-big-picture'``.
    """
    try:
        created = _audit.run_big_security_pass()
    except Exception as e:
        raise HTTPException(500, f"big-picture security pass failed: {e}")
    return {
        "created_ids": [c["id"] for c in created],
        "count": len(created),
        "items": created,
    }


@app.post("/api/requirements/{rid}/status")
def set_requirement_status(rid: str, body: RequirementStatus):
    # requirement → backlog 상태 매핑
    _req_to_backlog = {
        "planning":    "planning",
        "in_progress": "working",
        "done":        "done",
        "cancelled":   "cancelled",
        # "new" 는 기본 "next" 유지 — 매핑 없음
    }
    for item in REQUIREMENTS:
        if item["id"] == rid:
            prev = item["status"]
            item["status"] = body.status
            log_event(
                item.get("assigned_to") or "orchestrator",
                "requirement",
                f"요구사항 상태 {prev} → {body.status}",
            )
            # 같은 source_req_id 를 가진 backlog item 들 연동
            new_bstatus = _req_to_backlog.get(body.status)
            if new_bstatus:
                for b in BACKLOG:
                    if b.get("source_req_id") == rid:
                        b["status"] = new_bstatus
            _save_state()
            return item
    raise HTTPException(404, "requirement not found")


@app.post("/api/requirements/{rid}/cancel")
def cancel_requirement(rid: str):
    for item in REQUIREMENTS:
        if item["id"] == rid:
            if item["status"] == "done":
                raise HTTPException(400, "cannot cancel a completed requirement")
            prev = item["status"]
            item["status"] = "cancelled"
            log_event(
                item.get("assigned_to") or "orchestrator",
                "requirement",
                f"요구사항 취소됨 ({prev} → cancelled)",
            )
            # backlog 연동: cancelled 전파 + 실제로 상태가 바뀐 개수를
            # activity 로 1줄 남긴다 (이미 cancelled 였으면 skip).
            flipped = 0
            for b in BACKLOG:
                if b.get("source_req_id") == rid and b.get("status") != "cancelled":
                    b["status"] = "cancelled"
                    flipped += 1
            if flipped:
                log_event(
                    item.get("assigned_to") or "orchestrator",
                    "backlog",
                    f"요구사항 취소에 따라 백로그 {flipped}건 cancelled 로 전환",
                )
            # Stop any running coordinator for this rid as well.
            try:
                _coordinator.stop_coordinator(rid)
            except Exception:
                pass
            _save_state()
            return item
    raise HTTPException(404, "requirement not found")


# ── Backlog (populated only by real Claude Code work) ───────────────
@app.get("/api/backlog")
def get_backlog(exclude_cancelled: int = 0):
    """Return all backlog items. With ``?exclude_cancelled=1`` filter out
    any items whose source requirement was cancelled — lets the frontend
    keep a "live" next/working view without showing tombstones. Default
    stays on (include-all) for back-compat with existing callers."""
    items = list(BACKLOG)
    if exclude_cancelled:
        items = [b for b in items if (b.get("status") or "") != "cancelled"]
    return {"items": items}


@app.post("/api/backlog")
def create_backlog(b: BacklogIn):
    bid = str(uuid.uuid4())[:8]
    item = {
        "id": bid,
        "title": b.title,
        "team": b.team,
        "priority": b.priority,
        "status": "next",
        "source_req_id": b.source_req_id,
        "created_at": now_iso(),
    }
    BACKLOG.insert(0, item)
    log_event(b.team or "orchestrator", "backlog", f"백로그 추가: {b.title[:60]}")
    return item


@app.post("/api/backlog/{bid}/status")
def set_backlog_status(bid: str, body: BacklogStatus):
    for item in BACKLOG:
        if item["id"] == bid:
            prev = item.get("status")
            item["status"] = body.status
            log_event(
                item.get("team") or "orchestrator",
                "backlog",
                f"백로그 {bid} 상태 {prev} → {body.status}",
            )
            return item
    raise HTTPException(404, "backlog item not found")


@app.post("/api/backlog/{bid}")
def patch_backlog(bid: str, body: BacklogPatch):
    for item in BACKLOG:
        if item["id"] == bid:
            patch = body.model_dump(exclude_none=True)
            # id / created_at 불변
            patch.pop("id", None)
            patch.pop("created_at", None)
            item.update(patch)
            log_event(
                item.get("team") or "orchestrator",
                "backlog",
                f"백로그 {bid} 갱신: {', '.join(patch.keys()) or '(no-op)'}",
            )
            return item
    raise HTTPException(404, "backlog item not found")


# ── Cost ─────────────────────────────────────────────────────────────
@app.get("/api/cost")
def get_cost():
    return {
        "total": round(COST_TOTAL, 4),
        "by_model": {k: round(v, 4) for k, v in COST_BY_MODEL.items()},
        "tokens_by_model": TOKENS_BY_MODEL,
    }


# ── Health ───────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"ok": True, "templates_dir": str(TEMPLATES), "exists": TEMPLATES.exists()}


# ── MCPs ─────────────────────────────────────────────────────────────
MCPS = [
    {"id": "filesystem", "name_ko": "파일시스템 MCP", "name_en": "Filesystem MCP",
     "purpose_ko": "프로젝트 파일을 안전하게 읽고 쓰기 위한 도구.",
     "purpose_en": "Safely read and write project files.", "icon_tile": "fridge"},
    {"id": "browser",    "name_ko": "브라우저 MCP",   "name_en": "Browser MCP",
     "purpose_ko": "웹 페이지를 열어 DOM을 조작하거나 스크린샷을 찍어 에이전트가 실제 화면을 확인하게 합니다.",
     "purpose_en": "Open pages, manipulate DOM, capture screenshots.", "icon_tile": "water"},
    {"id": "shell",      "name_ko": "Shell MCP",      "name_en": "Shell MCP",
     "purpose_ko": "빌드/테스트/curl 같은 쉘 명령을 안전한 샌드박스에서 실행합니다.",
     "purpose_en": "Run build/test/curl commands in a sandboxed shell.", "icon_tile": "coffee"},
    {"id": "github",     "name_ko": "GitHub MCP",     "name_en": "GitHub MCP",
     "purpose_ko": "PR/이슈 조회, 리뷰 코멘트 수집 등 깃허브와 상호작용합니다.",
     "purpose_en": "Interact with GitHub repos: PRs, issues, reviews.", "icon_tile": "printer"},
    {"id": "memory",     "name_ko": "Memory MCP",     "name_en": "Memory MCP",
     "purpose_ko": "대화 간 오래 유지되어야 할 지식을 저장·조회합니다.",
     "purpose_en": "Store and retrieve long-lived knowledge.", "icon_tile": "server"},
]


@app.get("/api/mcps")
def get_mcps():
    return {"mcps": MCPS}


# ── Skills (Claude Code skill-like procedures) ──────────────────────
SKILLS = [
    {"id": "review",
     "label": "Code Review",
     "name_ko": "코드 리뷰",
     "name_en": "Code Review",
     "purpose_ko": "PR 또는 현재 변경점에 대한 종합 리뷰 — 로직·품질·보안·테스트 커버리지.",
     "purpose_en": "End-to-end review of current changes or a PR — logic, quality, security, test coverage."},
    {"id": "security-review",
     "label": "Security Review",
     "name_ko": "보안 리뷰",
     "name_en": "Security Review",
     "purpose_ko": "OWASP Top 10 기준 취약점 점검 — injection, XSS, SSRF, 권한 상승 등.",
     "purpose_en": "OWASP Top 10 style audit — injection, XSS, SSRF, privilege escalation, etc."},
    {"id": "simplify",
     "label": "Simplify",
     "name_ko": "단순화",
     "name_en": "Simplify",
     "purpose_ko": "변경된 코드에서 재사용 가능성 · 품질 · 효율성 이슈를 찾아 수정합니다.",
     "purpose_en": "Find reuse / quality / efficiency issues in changed code and fix them."},
    {"id": "init",
     "label": "Init",
     "name_ko": "CLAUDE.md 초기화",
     "name_en": "Init CLAUDE.md",
     "purpose_ko": "새 프로젝트에 CLAUDE.md 를 생성해 구조 · 규칙 · 실행 방법을 문서화합니다.",
     "purpose_en": "Create a fresh CLAUDE.md documenting structure, rules, and how to run the project."},
]


@app.get("/api/skills")
def get_skills():
    return {"skills": SKILLS}


# ── Org chart drill-down ────────────────────────────────────────────
@app.get("/api/org")
def get_org():
    loaded_names = {a["name"] for a in load_agents()}
    hierarchy = []
    for t in TEAMS:
        tid = t["id"]
        members = [
            name for name in loaded_names
            if team_of(name)[0] == tid
        ]
        hierarchy.append({
            "id": tid,
            "label_ko": t["label_ko"],
            "label_en": t["label_en"],
            "members": members,
        })
    return {"hierarchy": hierarchy}


# ── Providers ───────────────────────────────────────────────────────
PROVIDERS = [
    {"id": "anthropic",  "name": "Anthropic Claude",       "models": ["opus", "sonnet", "haiku"], "enabled": True,
     "note_ko": "Anthropic 공식 API — Claude Code CLI 기본", "note_en": "Official Anthropic API — default for Claude Code CLI"},
    {"id": "bedrock",    "name": "Amazon Bedrock (Claude)", "models": ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"], "enabled": True,
     "note_ko": "AWS Bedrock 경유 Claude",
     "note_en": "Claude via AWS Bedrock"},
]


@app.get("/api/providers")
def get_providers():
    return {"providers": PROVIDERS}


class ProviderKeysIn(BaseModel):
    anthropic:   str | None = None
    openai:      str | None = None
    gemini:      str | None = None
    elevenlabs:  str | None = None  # TTS/STT (voice-io 에이전트용)
    falai:       str | None = None  # 영상/이미지 생성 (video-maker 에이전트용)
    bedrock:     bool | str | None = None
    # Bedrock easy-connect slots (Windows-friendly — no need to edit
    # .env or run `setx` manually; these flow through PROVIDER_KEYS →
    # os.environ → boto3).
    aws_access_key_id:     str | None = None
    aws_secret_access_key: str | None = None
    aws_region:            str | None = None


@app.get("/api/providers/keys")
def get_provider_keys():
    """Return masked view of configured keys. For key-like slots
    (anthropic/openai/gemini/aws_access_key_id/aws_secret_access_key)
    the response is ``"sk-…abcd"`` when set (from UI OR env) else null.
    ``bedrock`` is a bool (``CLAUDE_CODE_USE_BEDROCK=="1"``); ``aws_region``
    is returned in the clear (it's not a secret)."""
    def _resolved(slot: str) -> str:
        # UI-saved value wins; else whatever env already has (e.g. .env).
        envname = _PROVIDER_ENV_MAP[slot]
        return PROVIDER_KEYS.get(slot) or os.environ.get(envname) or ""

    return {
        "anthropic":             _mask_key(_resolved("anthropic"))  or None,
        "openai":                _mask_key(_resolved("openai"))     or None,
        "gemini":                _mask_key(_resolved("gemini"))     or None,
        "elevenlabs":            _mask_key(_resolved("elevenlabs")) or None,
        "falai":                 _mask_key(_resolved("falai"))      or None,
        "bedrock":               _resolved("bedrock") == "1",
        "aws_access_key_id":     _mask_key(_resolved("aws_access_key_id"))     or None,
        "aws_secret_access_key": _mask_key(_resolved("aws_secret_access_key")) or None,
        "aws_region":            _resolved("aws_region") or None,
        # Hint for the UI: which slots are locked by env (user cannot
        # clear them from UI — they'd need to unset the shell export).
        "env_locked": {
            slot: bool(os.environ.get(_PROVIDER_ENV_MAP[slot]))
                  and not PROVIDER_KEYS.get(slot)
            for slot in _PROVIDER_ENV_MAP
        },
    }


@app.post("/api/providers/bedrock/test")
def test_bedrock_connection():
    """One-click Bedrock connectivity check.

    Runs a minimal ``converse`` call against the configured model and
    reports back {ok, latency_ms, model, sample | error, hint}. Designed
    for the ProviderKeysPanel "Test connection" button — surfaces the
    usual AWS onboarding errors in plain Korean so the user doesn't have
    to dig through boto3 tracebacks.
    """
    region = os.environ.get("AWS_REGION", "")
    model = os.environ.get("ANTHROPIC_MODEL", "anthropic.claude-opus-4-7-v1:0")
    if not region:
        return {
            "ok": False,
            "error": "AWS_REGION 미설정",
            "hint": "Provider 패널에서 Region 입력 (예: us-east-1, us-west-2, ap-northeast-2).",
        }
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        return {
            "ok": False,
            "error": "AWS_ACCESS_KEY_ID 미설정",
            "hint": "Provider 패널에서 AWS Access Key ID 입력.",
        }
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        return {
            "ok": False,
            "error": "boto3 미설치",
            "hint": "`pip install boto3` 후 서버 재기동.",
        }
    t0 = time.time()
    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        resp = client.converse(
            modelId=model,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            inferenceConfig={"maxTokens": 32},
        )
        out = resp.get("output", {}).get("message", {})
        parts = [c.get("text", "") for c in out.get("content", []) if c.get("text")]
        sample = "\n".join(parts)[:120]
        return {
            "ok": True,
            "latency_ms": int((time.time() - t0) * 1000),
            "model": model,
            "region": region,
            "sample": sample,
        }
    except NoCredentialsError:
        return {
            "ok": False,
            "error": "AWS 자격증명이 실제 boto3 에 전달되지 않음",
            "hint": "Provider 패널에서 저장 후 서버가 값을 받았는지 확인. Windows 의 기존 AWS 프로파일과 충돌 가능성.",
        }
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        msg = e.response.get("Error", {}).get("Message", str(e))
        hints = {
            "AccessDeniedException":  "IAM 정책에 `bedrock:InvokeModel` 권한 추가 필요. AWS 콘솔 → IAM → 해당 유저/역할 → Policies.",
            "ValidationException":    f"모델 ID '{model}' 가 이 리전에서 활성화 안 됐을 수 있음. AWS 콘솔 → Bedrock → Model access 에서 Opus 4.7 요청/승인.",
            "ResourceNotFoundException": f"모델 '{model}' 미존재. ANTHROPIC_MODEL 환경변수 확인 (예: anthropic.claude-opus-4-7-v1:0).",
            "ThrottlingException":    "리전 quota 초과. 잠시 후 재시도 또는 quota 증설 요청.",
            "UnrecognizedClientException": "Access Key / Secret 값이 잘못됨. 다시 입력.",
        }
        return {
            "ok": False,
            "error": f"{code}: {msg}",
            "hint": hints.get(code, "AWS 콘솔에서 해당 에러 코드를 검색."),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "hint": "예상 못한 오류 — 로그 확인."}


@app.post("/api/providers/keys")
def set_provider_keys(body: ProviderKeysIn):
    """Upsert/remove provider keys.

    Semantics per slot:
      • value is a non-empty string → save + inject os.environ[envname]
      • value is ``""`` or ``null`` → drop from PROVIDER_KEYS AND pop
        os.environ[envname]. (User explicitly cleared; env mirror goes
        with it so next LLM call falls back to the next provider.)
    For ``bedrock``, accept bool OR "1"/"0" strings — stored as "1"/"".
    """
    payload = body.model_dump(exclude_unset=True)
    touched: list[str] = []

    for slot, envname in _PROVIDER_ENV_MAP.items():
        if slot not in payload:
            continue
        raw = payload[slot]
        if slot == "bedrock":
            if raw in (True, "1", 1, "true", "True"):
                PROVIDER_KEYS[slot] = "1"
                os.environ[envname] = "1"
            else:
                PROVIDER_KEYS.pop(slot, None)
                os.environ.pop(envname, None)
        else:
            s = (raw or "").strip() if isinstance(raw, str) else ""
            if s:
                PROVIDER_KEYS[slot] = s
                os.environ[envname] = s
            else:
                PROVIDER_KEYS.pop(slot, None)
                os.environ.pop(envname, None)
        touched.append(slot)

    _save_state()
    return {"ok": True, "touched": touched, **get_provider_keys()}


# ── Knowledge base (self-evolution, scoped to active project) ───────
def _knowledge_file() -> Path:
    slug = get_active_project()
    if slug:
        return _project_dir(slug) / "knowledge.json"
    return KNOWLEDGE_FILE_LEGACY


def load_knowledge() -> list[dict]:
    f = _knowledge_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_knowledge(items: list[dict]) -> None:
    f = _knowledge_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


KNOWLEDGE: list[dict] = load_knowledge()


@app.get("/api/knowledge")
def get_knowledge():
    return {"items": list(KNOWLEDGE)}


@app.post("/api/knowledge")
def add_knowledge(k: KnowledgeIn):
    kid = str(uuid.uuid4())[:8]
    item = {"id": kid, "agent": k.agent, "topic": k.topic, "insight": k.insight, "created": now_iso()}
    KNOWLEDGE.insert(0, item)
    save_knowledge(KNOWLEDGE)
    log_event(k.agent, "knowledge", f"지식 축적: {k.topic}")
    return item


# ── Evolution proposals (self-evo) ──────────────────────────────────
@app.get("/api/evolution")
def get_evolution():
    return {"items": list(EVOLUTION)}


@app.post("/api/evolution")
def propose_evolution(e: EvolutionIn):
    eid = str(uuid.uuid4())[:8]
    item = {
        "id": eid,
        "agent": e.agent,
        "kind": e.kind,
        "title": e.title,
        "rationale": e.rationale,
        "payload": e.payload or {},
        "status": "proposed",
        "created": now_iso(),
        "decided": None,
        "decision_note": None,
    }
    EVOLUTION.insert(0, item)
    log_event(e.agent, "evolution", f"자가진화 제안 [{e.kind}]: {e.title}")
    return item


@app.delete("/api/evolution/{eid}")
def delete_evolution(eid: str):
    """Remove an EVOLUTION proposal. Used by the audit-dedup cleanup
    flow to prune leftover duplicate cards (e.g. a rejected finding
    that was also accepted in parallel). No admin guard — the viewer
    runs on localhost.
    """
    for i, item in enumerate(EVOLUTION):
        if item.get("id") == eid:
            removed = EVOLUTION.pop(i)
            log_event(
                "user", "evolution",
                f"감사 제안 삭제({eid}): {removed.get('title', '')}"
            )
            _save_state()
            return {"ok": True, "id": eid, "title": removed.get("title")}
    raise HTTPException(404, "evolution proposal not found")


@app.post("/api/evolution/{eid}/decision")
def decide_evolution(eid: str, body: EvolutionDecision):
    for item in EVOLUTION:
        if item["id"] == eid:
            item["status"] = body.decision
            item["decided"] = now_iso()
            item["decision_note"] = body.note
            log_event("user", "evolution",
                      f"감사 제안 결정({eid}): {body.decision}" + (f" — {body.note}" if body.note else ""))
            # Accepted new_agent / retire_agent proposals must materialize
            # as actual roster changes — otherwise the audit tab is just
            # advisory. Mutates the active project's mission.json.
            if body.decision == "accepted" and item["kind"] in ("new_agent", "retire_agent"):
                _apply_roster_change(item)
            return item
    raise HTTPException(404, "evolution proposal not found")


def _apply_roster_change(item: dict):
    """Apply an accepted new_agent / retire_agent proposal to mission.json.

    Payload contract:
      { "name": "<agent-id>", "team": "dev" | "domain" }

    Only names present in DEV_CATALOG / DOMAIN_CATALOG are accepted;
    unknown names are ignored (the orchestrator can extend the catalog
    separately). The orchestrator + team-lead unanimity rule is applied
    upstream when the proposal is raised — by the time this function
    runs, the user has already countersigned the decision in the UI.
    """
    payload = item.get("payload") or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return
    mission = load_mission()
    dev = list(mission.get("dev_agents", []))
    domain = list(mission.get("domain_agents", []))
    if item["kind"] == "new_agent":
        if name in DEV_CATALOG and name not in dev:
            dev.append(name)
        elif name in DOMAIN_CATALOG and name not in domain:
            domain.append(name)
        else:
            return
        log_event("orchestrator", "team",
                  f"감사 수락 → 에이전트 추가: {name}")
    elif item["kind"] == "retire_agent":
        if name in dev:
            dev.remove(name)
        elif name in domain:
            domain.remove(name)
        else:
            return
        log_event("orchestrator", "team",
                  f"감사 수락 → 에이전트 정리: {name}")
    mission["dev_agents"] = dev
    mission["domain_agents"] = domain
    save_mission(mission)


# ── Web chat (orchestrator-backed) ──────────────────────────────────
# Two modes of operation:
#   1. `stub` (no env) — echoes a structured fake response so the UI
#      flow can be exercised before real API keys are wired up.
#   2. `anthropic` — uses ANTHROPIC_API_KEY with the Anthropic SDK.
#   3. `bedrock`   — uses AWS_REGION + IAM creds with AWS Bedrock
#      converse / invoke-model. Requires `boto3`.
#
# The orchestrator's system prompt is assembled from:
#   - `mission.json` (company / industry / philosophy / goal)
#   - The active project's confirmed team roster (dev_agents + domain_agents)
#   - The canonical orchestrator.md template body
#
# Subagent delegation: handled by Claude's tool_use. A single tool,
# `call_subagent(name, prompt)`, is exposed; when the orchestrator calls
# it, we load that subagent's template body as its system prompt, spin
# up a second Claude turn, and return the result back into the main
# conversation. Each subagent call also POSTs state/activity so the
# viewer lights up just like hook-driven flows.

class ChatIn(BaseModel):
    message: str
    project_slug: str | None = None   # override active project, optional
    history: list[dict] | None = None # [{role, content}]


def _detect_provider() -> str:
    """Pick the strongest provider available. Priority matches
    ``translator._llm_call``: anthropic > bedrock > openai > gemini > stub.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1" or os.environ.get("AWS_ACCESS_KEY_ID"):
        return "bedrock"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "stub"


def _orchestrator_system_prompt() -> str:
    mission = load_mission()
    orch_md = TEMPLATES / "orchestrator.md"
    body = ""
    if orch_md.exists():
        _, body = parse_frontmatter(orch_md.read_text(encoding="utf-8"))
    roster = ", ".join(current_roster())
    return (
        f"# 프로젝트 컨텍스트\n"
        f"회사: {mission.get('company') or '—'}\n"
        f"업종: {mission.get('industry') or '—'}\n"
        f"철학: {mission.get('philosophy') or '—'}\n"
        f"목표: {mission.get('goal') or '—'}\n\n"
        f"활성 에이전트 로스터: {roster}\n\n"
        f"# 역할\n{body}\n"
    )


def _call_anthropic(message: str, history: list[dict]) -> str:
    try:
        from anthropic import Anthropic
    except Exception as e:
        return f"[anthropic SDK not installed: {e}]"
    client = Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
    msgs = list(history or []) + [{"role": "user", "content": message}]
    resp = client.messages.create(
        model=model,
        max_tokens=1500,
        system=_orchestrator_system_prompt(),
        messages=msgs,
    )
    parts = []
    for blk in resp.content:
        if getattr(blk, "type", None) == "text":
            parts.append(blk.text)
    return "\n".join(parts) or "[empty response]"


def _call_bedrock(message: str, history: list[dict]) -> str:
    try:
        import boto3
    except Exception as e:
        return f"[boto3 not installed: {e}]"
    region = os.environ.get("AWS_REGION", "us-east-1")
    model = os.environ.get("ANTHROPIC_MODEL", "anthropic.claude-opus-4-7-v1:0")
    client = boto3.client("bedrock-runtime", region_name=region)
    msgs = [
        {"role": m.get("role", "user"),
         "content": [{"text": str(m.get("content", ""))}]}
        for m in (history or [])
    ] + [{"role": "user", "content": [{"text": message}]}]
    resp = client.converse(
        modelId=model,
        messages=msgs,
        system=[{"text": _orchestrator_system_prompt()}],
        inferenceConfig={"maxTokens": 1500},
    )
    out = resp.get("output", {}).get("message", {})
    parts = [c.get("text", "") for c in out.get("content", []) if c.get("text")]
    return "\n".join(parts) or "[empty response]"


def _call_stub(message: str, history: list[dict]) -> str:
    mission = load_mission()
    return (
        f"[STUB 응답 — 실제 LLM 연결 안 됨]\n\n"
        f"orchestrator 가 '{mission.get('company') or 'this project'}' 맥락에서 "
        f"질문 '{message[:120]}' 을 받았습니다.\n\n"
        f"실제 응답을 받으려면 다음 중 하나를 세팅하세요:\n"
        f"  • `ANTHROPIC_API_KEY` — Anthropic 공식 API\n"
        f"  • `CLAUDE_CODE_USE_BEDROCK=1` + AWS 자격증명 — Amazon Bedrock\n\n"
        f"HUD 의 ☁ 가이드 버튼에 Bedrock 세팅 단계가 있습니다."
    )


@app.post("/api/chat")
def api_chat(body: ChatIn):
    # Route to the right project's context if requested
    if body.project_slug and _project_dir(body.project_slug).exists():
        set_active_project(body.project_slug)
    provider = _detect_provider()
    log_event("orchestrator", "chat", f"사용자 질문 수신 ({provider}): " + body.message[:80])
    STATES["orchestrator"] = "working"
    try:
        if provider == "bedrock":
            reply = _call_bedrock(body.message, body.history or [])
        elif provider == "anthropic":
            reply = _call_anthropic(body.message, body.history or [])
        elif provider in ("openai", "gemini"):
            # Flatten history into the user turn; translator._llm_call is
            # single-turn (system + user). Good enough for chat fallback —
            # if users want full multi-turn they can wire ANTHROPIC_API_KEY.
            from translator import _llm_call as _t_llm_call  # type: ignore
            hist_text = "\n".join(
                f"{m.get('role','user')}: {m.get('content','')}"
                for m in (body.history or [])
            )
            user_blob = (hist_text + "\n\n" + body.message).strip() if hist_text else body.message
            reply = _t_llm_call(_orchestrator_system_prompt(), user_blob) \
                or _call_stub(body.message, body.history or [])
        else:
            reply = _call_stub(body.message, body.history or [])
    except Exception as e:
        reply = f"[chat failed: {e}]"
    finally:
        STATES["orchestrator"] = "idle"
    log_event("orchestrator", "chat", "답변 완료: " + reply[:80])
    return {"provider": provider, "reply": reply}


@app.get("/api/chat/provider")
def api_chat_provider():
    return {"provider": _detect_provider()}


@app.on_event("startup")
async def _boot():
    log_event("system", "boot", "OmniHarness Viewer 가동 — 실제 작업 대기 중")
    # Capture the running event loop so sync endpoints (running on
    # FastAPI's threadpool) can schedule coordinator coroutines back
    # onto the main loop.
    try:
        _coordinator.set_main_loop(asyncio.get_running_loop())
    except Exception:
        pass


# ── Serve SPA ────────────────────────────────────────────────────────
DIST = Path(__file__).parent.parent / "frontend" / "dist"
if DIST.exists():
    if (DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="assets")
    if (DIST / "tiles").exists():
        app.mount("/tiles", StaticFiles(directory=str(DIST / "tiles")), name="tiles")

    @app.get("/{path:path}")
    def serve_spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API not found")
        fp = DIST / path
        if fp.exists() and fp.is_file():
            return FileResponse(str(fp))
        return FileResponse(str(DIST / "index.html"))
