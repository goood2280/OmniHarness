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

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

# ── Roles ────────────────────────────────────────────────────────────
# BASE: always present regardless of project. These are the universal
# coordination + evaluation + management roles.
# DYNAMIC (dev + domain): proposed per project during onboarding, added
# to the roster on confirmation.
#
# Each entry: name → (team_id, label_color)
BASE_ROLES: dict[str, tuple[str, str]] = {
    "orchestrator":      ("top",   "#E87722"),
    "dev-lead":          ("leads", "#7cc7e8"),
    "mgmt-lead":         ("leads", "#b48f5c"),
    "eval-lead":         ("leads", "#ff9b9b"),
    "reporter":          ("mgmt",  "#b48f5c"),
    "hr":                ("mgmt",  "#8a6a3a"),
    "ux-reviewer":       ("eval",  "#ff9b9b"),
    "dev-verifier":      ("eval",  "#e57373"),
    "user-role-tester":  ("eval",  "#a56c4c"),
    "admin-role-tester": ("eval",  "#8c5a3c"),
    "security-auditor":  ("eval",  "#7a6650"),
    "domain-researcher": ("eval",  "#6c5a44"),
}

# Candidate dev/domain templates that MAY be proposed by the orchestrator.
# These are catalog entries — only the confirmed subset becomes part of
# the live roster.
DEV_CATALOG = [
    "dev-dashboard", "dev-spc", "dev-wafer-map", "dev-ml", "dev-ettime",
    "dev-tablemap", "dev-tracker", "dev-filebrowser", "dev-admin", "dev-messages",
]
DOMAIN_CATALOG = [
    "process-tagger", "causal-analyst", "dvc-curator", "adapter-engineer",
]

TEAMS = [
    {"id": "top",    "label_ko": "총괄",         "label_en": "HQ"},
    {"id": "leads",  "label_ko": "팀 리드",       "label_en": "Team Leads"},
    {"id": "dev",    "label_ko": "개발팀",        "label_en": "Dev Team"},
    {"id": "domain", "label_ko": "도메인 전문",   "label_en": "Domain Specialists"},
    {"id": "mgmt",   "label_ko": "경영지원팀",    "label_en": "Management Support"},
    {"id": "eval",   "label_ko": "평가팀",        "label_en": "Evaluation"},
]

State = Literal["idle", "working", "waiting"]

# ── Pricing (approximate 2026 rates, USD per 1M tokens) ──────────────
PRICING = {
    "opus":   {"in": 15.0,  "out": 75.0},
    "sonnet": {"in": 3.0,   "out": 15.0},
    "haiku":  {"in": 1.0,   "out": 5.0},
}

# ── In-memory state ──────────────────────────────────────────────────
STATES: dict[str, State] = {}
COST_TOTAL: float = 0.0
COST_BY_MODEL: dict[str, float] = {"opus": 0.0, "sonnet": 0.0, "haiku": 0.0}
TOKENS_BY_MODEL: dict[str, dict] = {
    "opus":   {"in": 0, "out": 0},
    "sonnet": {"in": 0, "out": 0},
    "haiku":  {"in": 0, "out": 0},
}

ACTIVITY: deque = deque(maxlen=300)

QUESTIONS: list[dict] = []
REPORTS: list[dict] = []
REQUIREMENTS: list[dict] = []
BACKLOG: list[dict] = []
EVOLUTION: list[dict] = []

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


class RequirementStatus(BaseModel):
    status: Literal["new", "planning", "in_progress", "done", "cancelled"]


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
    roster = list(BASE_ROLES.keys()) + [n for n in dev if n in DEV_CATALOG] + [n for n in domain if n in DOMAIN_CATALOG]
    return roster


def team_of(name: str) -> tuple[str, str]:
    if name in BASE_ROLES:
        return BASE_ROLES[name]
    if name in DEV_CATALOG:
        return ("dev", "#7cc7e8")
    if name in DOMAIN_CATALOG:
        return ("domain", "#ffd54f")
    return ("misc", "#999999")


def load_agents() -> list[dict]:
    agents = []
    roster = set(current_roster())
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
    teams_out = []
    for t in TEAMS:
        members = [a["name"] for a in agents if a["team"] == t["id"]]
        teams_out.append({**t, "members": members})
    pending_q = sum(1 for q in QUESTIONS if q["status"] in ("pending_user",))
    pending_req = sum(1 for r in REQUIREMENTS if r["status"] not in ("done", "cancelled"))
    pending_evo = sum(1 for e in EVOLUTION if e["status"] == "proposed")
    return {
        "agents": agents,
        "teams": teams_out,
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
    item = {
        "id": qid,
        "agent": q.agent,
        "raw": q.raw,
        "translated": None,
        "answer": None,
        "answer_structured": None,
        "context": q.context,
        "status": "pending_translation",
        "created": now_iso(),
        "answered": None,
    }
    QUESTIONS.insert(0, item)
    log_event(q.agent, "question", "질문 제기: " + q.raw[:48])
    return item


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
    """Heuristic roster proposal based on industry keywords.

    This is a *default* proposal; the real Claude Code orchestrator can
    call /api/mission with a more informed suggestion. The viewer just
    needs something reasonable to show in the onboarding wizard."""
    industry = (mission.get("industry") or "").lower()
    goal = (mission.get("goal") or "").lower()
    blob = f"{industry} {goal}"

    dev: list[str] = []
    reason_parts: list[str] = []

    # Always a dashboard + an admin console for any web app
    dev.extend(["dev-dashboard", "dev-admin"])

    if any(k in blob for k in ["semicon", "fab", "반도체", "wafer", "yield", "수율"]):
        dev.extend(["dev-spc", "dev-wafer-map", "dev-ml", "dev-tablemap"])
        domain = ["process-tagger", "causal-analyst", "dvc-curator", "adapter-engineer"]
        reason_parts.append("반도체/수율 도메인 감지 → SPC · Wafer Map · ML + 공정 전문가 4인")
    elif any(k in blob for k in ["commerce", "shop", "쇼핑", "retail", "order"]):
        dev.extend(["dev-tracker", "dev-messages", "dev-filebrowser"])
        domain = []
        reason_parts.append("이커머스 도메인 감지 → 주문/메시지/파일 관리")
    elif any(k in blob for k in ["data", "analytics", "분석", "ml", "ai", "model"]):
        dev.extend(["dev-ml", "dev-tablemap", "dev-ettime"])
        domain = ["causal-analyst", "dvc-curator"]
        reason_parts.append("데이터/분석 도메인 감지 → ML · 테이블맵 + 분석 전문가")
    else:
        # Generic web product
        dev.extend(["dev-tracker", "dev-filebrowser", "dev-messages"])
        domain = []
        reason_parts.append("범용 웹 프로젝트로 판단 → 트래커/파일/메시지 기능 커버")

    # Deduplicate while preserving order
    def dedup(xs):
        seen = set()
        out = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    dev = dedup([x for x in dev if x in DEV_CATALOG])
    domain = dedup([x for x in domain if x in DOMAIN_CATALOG])
    reason = "  •  ".join(reason_parts)
    return dev, domain, reason


@app.post("/api/mission/propose_team")
def propose_team():
    mission = load_mission()
    if mission.get("placeholder"):
        raise HTTPException(400, "mission must be set first")
    dev, domain, reason = _propose_team(mission)
    mission["proposed_dev_agents"] = dev
    mission["proposed_domain_agents"] = domain
    mission["proposal_reason"] = reason
    save_mission(mission)
    log_event("orchestrator", "team", f"팀 구성 제안 — dev {len(dev)} · domain {len(domain)}")
    return mission


@app.post("/api/mission/confirm_team")
def confirm_team(body: TeamConfirm):
    dev = [x for x in body.dev_agents if x in DEV_CATALOG]
    domain = [x for x in body.domain_agents if x in DOMAIN_CATALOG]
    mission = load_mission()
    mission["dev_agents"] = dev
    mission["domain_agents"] = domain
    mission["team_confirmed"] = True
    save_mission(mission)
    log_event("orchestrator", "team", f"팀 구성 확정 — dev {len(dev)} · domain {len(domain)}")
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
    return {
        "title_ko": "Amazon Bedrock 으로 Claude Code CLI 운영",
        "title_en": "Run Claude Code CLI on Amazon Bedrock",
        "sections_ko": [
            {"h": "왜 Bedrock?",
             "body": "사내 AWS 계정이 이미 있다면, 별도 Anthropic 계약 없이 회사 결제/감사 체계 안에서 Claude 모델을 쓸 수 있습니다. 데이터가 AWS 경계 안에 머무르고, IAM 으로 접근 통제가 됩니다."},
            {"h": "1. 모델 접근 승인",
             "body": "AWS 콘솔 → Bedrock → 왼쪽 `Model access` → `Manage model access` → Anthropic 모델 (Claude 4.x Opus/Sonnet/Haiku) 체크 후 Submit. 승인까지 몇 분~수 시간."},
            {"h": "2. AWS 자격증명 설정",
             "body": "`aws configure` 로 AccessKey/Secret/Region 입력 (권장 리전: us-east-1 또는 us-west-2). IAM 유저에는 `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` 권한 필요."},
            {"h": "3. Claude Code CLI 환경변수",
             "body": "쉘 rc 파일(.zshrc / .bashrc) 에 추가:\n\n```\nexport CLAUDE_CODE_USE_BEDROCK=1\nexport AWS_REGION=us-east-1\nexport ANTHROPIC_MODEL=anthropic.claude-opus-4-7-v1:0\nexport ANTHROPIC_SMALL_FAST_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0\n```"},
            {"h": "4. OmniHarness 와 연결 (두 가지 경로)",
             "body": "A) CLI 경로 — 프로젝트 디렉토리에서 `claude` 실행 시, `.claude/settings.json` 의 훅이 OmniHarness 뷰어(`OMNIHARNESS_URL`, 기본 http://localhost:8082)로 에이전트 상태를 밀어 넣습니다.\n\nB) 웹 경로 — 뷰어 우측 하단의 💬 질문하기 채팅으로 orchestrator 에게 바로 질문할 수 있습니다. 백엔드에 `CLAUDE_CODE_USE_BEDROCK=1` 과 AWS 자격증명이 설정되어 있으면 Bedrock 의 Claude Opus 가 응답하고, 없으면 STUB 로 동작합니다. Anthropic 공식 API 를 쓰려면 `ANTHROPIC_API_KEY` 만 설정하면 됩니다."},
            {"h": "검증",
             "body": "`claude --version` 이 실행되고 간단한 프롬프트에 응답하면 성공. 에러 발생 시 `aws bedrock list-foundation-models --region us-east-1` 로 모델 목록이 보이는지 먼저 확인."},
        ],
        "sections_en": [
            {"h": "Why Bedrock?",
             "body": "If you already have an AWS account, you can use Claude models through your existing billing/audit boundary without a separate Anthropic contract. Data stays inside AWS; IAM controls access."},
            {"h": "1. Request model access",
             "body": "AWS Console → Bedrock → `Model access` → `Manage model access` → check Anthropic models (Claude 4.x Opus/Sonnet/Haiku) → Submit. Approval takes minutes to hours."},
            {"h": "2. Configure AWS credentials",
             "body": "`aws configure` with Access Key / Secret / Region (recommend us-east-1 or us-west-2). IAM user needs `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`."},
            {"h": "3. Claude Code CLI env vars",
             "body": "Add to shell rc:\n\n```\nexport CLAUDE_CODE_USE_BEDROCK=1\nexport AWS_REGION=us-east-1\nexport ANTHROPIC_MODEL=anthropic.claude-opus-4-7-v1:0\nexport ANTHROPIC_SMALL_FAST_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0\n```"},
            {"h": "4. Wire into OmniHarness (two paths)",
             "body": "A) CLI path — running `claude` inside a project dir: hooks in `.claude/settings.json` push agent state to the viewer (env `OMNIHARNESS_URL`, default http://localhost:8082).\n\nB) Web path — the 💬 chat dock (bottom-right) talks to the orchestrator directly. With `CLAUDE_CODE_USE_BEDROCK=1` + AWS creds in the backend env, it runs on Bedrock Claude Opus. With `ANTHROPIC_API_KEY`, it uses the Anthropic API. Without either, it returns STUB responses so you can still exercise the UI flow."},
            {"h": "Verification",
             "body": "`claude --version` works and answers a simple prompt. On error, first verify `aws bedrock list-foundation-models --region us-east-1` returns the models."},
        ],
    }


# ── Requirements ────────────────────────────────────────────────────
@app.get("/api/requirements")
def list_requirements():
    return {"requirements": list(REQUIREMENTS)}


@app.post("/api/requirements")
def create_requirement(r: RequirementIn):
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
    return item


@app.post("/api/requirements/{rid}/status")
def set_requirement_status(rid: str, body: RequirementStatus):
    for item in REQUIREMENTS:
        if item["id"] == rid:
            prev = item["status"]
            item["status"] = body.status
            log_event(
                item.get("assigned_to") or "orchestrator",
                "requirement",
                f"요구사항 상태 {prev} → {body.status}",
            )
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
            return item
    raise HTTPException(404, "requirement not found")


# ── Backlog (populated only by real Claude Code work) ───────────────
@app.get("/api/backlog")
def get_backlog():
    return {"items": list(BACKLOG)}


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


@app.post("/api/evolution/{eid}/decision")
def decide_evolution(eid: str, body: EvolutionDecision):
    for item in EVOLUTION:
        if item["id"] == eid:
            item["status"] = body.decision
            item["decided"] = now_iso()
            item["decision_note"] = body.note
            log_event("user", "evolution",
                      f"자가진화 결정({eid}): {body.decision}" + (f" — {body.note}" if body.note else ""))
            return item
    raise HTTPException(404, "evolution proposal not found")


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
    """Pick the strongest provider available."""
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1" or os.environ.get("AWS_ACCESS_KEY_ID"):
        return "bedrock"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
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
