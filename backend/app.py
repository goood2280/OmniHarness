"""OmniHarness Viewer — FastAPI backend (v0.3).

Endpoints:
- GET  /api/topology           org chart + per-agent state
- GET  /api/states             lightweight states only
- POST /api/agents/{name}/state push live state (for external hooks)

- GET  /api/activity           recent activity log (ring buffer)
- POST /api/activity           append a log event (from hooks)

- GET  /api/questions          pending + recent questions
- POST /api/questions          agent submits a raw question
- POST /api/questions/{id}/translate  mgmt-lead sets user-friendly text
- POST /api/questions/{id}/answer     user's answer (resolves the question)

- GET  /api/reports            reporter-generated summary reports
- GET  /api/reports/{id}       single report (markdown body)
- POST /api/reports            reporter creates a new report

- GET  /api/cost               cumulative API cost (total + per-model breakdown)

- GET  /api/mcps               MCP descriptors for the kitchen appliance sprites
- GET  /api/org                hierarchical org chart (for OrgChart drill-down)
- GET  /api/providers          LLM provider presets (placeholder for UI)

- /                            serves the Vite-built SPA from ../frontend/dist

Run: cd OmniHarness/backend && uvicorn app:app --host 0.0.0.0 --port 8081
"""
from __future__ import annotations

import random
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).parent.parent
TEMPLATES = ROOT / "templates" / "agents"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
MISSION_FILE = ROOT / "mission.json"

DEFAULT_MISSION = {
    "company": "",
    "industry": "",
    "philosophy": "",
    "goal": "",
    "placeholder": True,
}

# ── Org chart (v0.4 — reorganized for FabCanvas feature ownership) ───
# Teams: top / leads / dev (feature-owners) / domain (specialists) /
#        mgmt (reporter+hr) / eval (testers+reviewers+researchers).
# The 18 Tier-3 members cover: 10 full-stack feature owners + 4 domain
# specialists + 4 evaluation roles, aligned to FabCanvas.ai modules.
ROLE = {
    "orchestrator":        ("top",    "fox",     "🦊", "#E87722"),
    "dev-lead":            ("leads",  "bear",    "🐻", "#8B5A2B"),
    "mgmt-lead":           ("leads",  "bear",    "🐻", "#8B5A2B"),
    "eval-lead":           ("leads",  "bear",    "🐻", "#8B5A2B"),
    # Dev feature owners (full-stack, FabCanvas.ai modules)
    "dev-dashboard":       ("dev",    "rabbit",  "🐰", "#F4B8B8"),
    "dev-spc":             ("dev",    "rabbit",  "🐇", "#D9F4B8"),
    "dev-wafer-map":       ("dev",    "owl",     "🦉", "#B8E0F4"),
    "dev-ml":              ("dev",    "owl",     "🦉", "#DFB8F4"),
    "dev-ettime":          ("dev",    "owl",     "🦉", "#F4D4B8"),
    "dev-tablemap":        ("dev",    "rat",     "🐀", "#C0C8D4"),
    "dev-tracker":         ("dev",    "rat",     "🐀", "#C8B88C"),
    "dev-filebrowser":     ("dev",    "rat",     "🐁", "#AFBBCC"),
    "dev-admin":           ("dev",    "rabbit",  "🐰", "#CCB8F4"),
    "dev-messages":        ("dev",    "owl",     "🦉", "#F4B8D4"),
    # Domain specialists (knowledge custodians, dev-lead's extended bench)
    "process-tagger":      ("domain", "raccoon", "🦝", "#B4935C"),
    "causal-analyst":      ("domain", "hedgehog","🦔", "#9A7A4C"),
    "dvc-curator":         ("domain", "raccoon", "🦝", "#B48F5C"),
    "adapter-engineer":    ("domain", "badger",  "🦡", "#A0825C"),
    # Management support (user-facing translation + harness stewardship)
    "reporter":            ("mgmt",   "raccoon", "🦝", "#7A5F47"),
    "hr":                  ("mgmt",   "owl",     "🦉", "#5C3E2A"),
    # Evaluation
    "ux-reviewer":         ("eval",   "badger",  "🦡", "#6C6C6C"),
    "dev-verifier":        ("eval",   "badger",  "🦡", "#6C6C6C"),
    "user-role-tester":    ("eval",   "fox",     "🦊", "#A56C4C"),
    "admin-role-tester":   ("eval",   "fox",     "🦊", "#8C5A3C"),
    "security-auditor":    ("eval",   "hedgehog","🦔", "#7A6650"),
    "domain-researcher":   ("eval",   "owl",     "🦉", "#6C5A44"),
}

TEAMS = [
    {"id": "top",    "label": "총괄"},
    {"id": "leads",  "label": "팀 리드"},
    {"id": "dev",    "label": "개발팀"},
    {"id": "domain", "label": "도메인 전문"},
    {"id": "mgmt",   "label": "경영지원팀"},
    {"id": "eval",   "label": "평가팀"},
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
# The viewer only lights up for REAL work pushed through hooks
# (FabCanvas.ai/.claude/settings.json → /api/agents/{name}/state).

COST_TOTAL: float = 0.0
COST_BY_MODEL: dict[str, float] = {"opus": 0.0, "sonnet": 0.0, "haiku": 0.0}
TOKENS_BY_MODEL: dict[str, dict] = {
    "opus":   {"in": 0, "out": 0},
    "sonnet": {"in": 0, "out": 0},
    "haiku":  {"in": 0, "out": 0},
}

ACTIVITY: deque = deque(maxlen=300)  # recent events

QUESTIONS: list[dict] = []
REPORTS: list[dict] = []
REQUIREMENTS: list[dict] = []
BACKLOG: list[dict] = []

# ── Models ───────────────────────────────────────────────────────────
class StateUpdate(BaseModel):
    state: State


class ActivityEvent(BaseModel):
    agent: str
    kind: str     # e.g. "state", "tool", "error", "question", "report"
    detail: str


class QuestionIn(BaseModel):
    agent: str
    raw: str       # technical wording from the agent
    context: str | None = None  # optional path/module context


class QuestionTranslate(BaseModel):
    translated: str
    translator: str = "mgmt-lead"


class QuestionAnswer(BaseModel):
    answer: str


class ReportIn(BaseModel):
    title: str
    content_md: str
    author: str = "reporter"


class MissionIn(BaseModel):
    company: str = ""
    industry: str
    philosophy: str
    goal: str


class RequirementIn(BaseModel):
    text: str
    assigned_to: str | None = None


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


def load_agents() -> list[dict]:
    agents = []
    for f in sorted(TEMPLATES.glob("*.md")):
        if f.stem.lower() == "readme":
            continue
        meta, body = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not meta or "name" not in meta:
            continue
        team, species, emoji, color = ROLE.get(
            meta["name"], ("misc", "mouse", "🐾", "#999999")
        )
        meta.update({
            "team": team, "species": species, "emoji": emoji, "color": color,
            "body": body, "state": STATES.get(meta["name"], "idle"),
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
    """Look up the `model:` frontmatter attribute from the agent's template, if any."""
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
    # Prefer explicit frontmatter model attribute when present
    attr = _agent_model_attr(agent_name)
    if attr:
        if "haiku" in attr:
            return "haiku"
        if "opus" in attr:
            return "opus"
        if "sonnet" in attr:
            return "sonnet"
    # Otherwise infer from org chart tier
    team = ROLE.get(agent_name, ("misc",))[0]
    return "opus" if team in ("top", "leads") else "sonnet"


def _tier_of(agent_name: str) -> int:
    """Return 1 for orchestrator (top), 2 for leads, 3 for members."""
    team = ROLE.get(agent_name, ("misc",))[0]
    if team == "top":
        return 1
    if team == "leads":
        return 2
    return 3


def accrue_cost(agent_name: str, tokens_in: int, tokens_out: int) -> float:
    global COST_TOTAL
    model = model_of(agent_name)
    price = PRICING[model]
    delta = (tokens_in * price["in"] + tokens_out * price["out"]) / 1_000_000
    COST_TOTAL += delta
    COST_BY_MODEL[model] = COST_BY_MODEL.get(model, 0.0) + delta
    TOKENS_BY_MODEL[model]["in"] += tokens_in
    TOKENS_BY_MODEL[model]["out"] += tokens_out
    return delta


def _accrue_for_state_working(agent_name: str) -> None:
    """Called when an agent transitions INTO state=working. Accrues a realistic
    per-invocation token estimate based on tier and explicit model attr."""
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
            if model == "opus":
                tokens_in, tokens_out = 2000, 1000
            else:
                tokens_in, tokens_out = 900, 450
    accrue_cost(agent_name, tokens_in, tokens_out)


# ── FastAPI app ──────────────────────────────────────────────────────
app = FastAPI(title="OmniHarness Viewer", version="0.3.0")


@app.get("/api/topology")
def topology():
    agents = load_agents()
    teams = [
        {**t, "members": [a["name"] for a in agents if a["team"] == t["id"]]}
        for t in TEAMS
    ]
    pending_q = sum(1 for q in QUESTIONS if q["status"] == "pending_user")
    pending_req = sum(1 for r in REQUIREMENTS if r["status"] not in ("done", "cancelled"))
    return {
        "agents": agents,
        "teams": teams,
        "total": len(agents),
        "cost_total": round(COST_TOTAL, 4),
        "cost_by_model": {k: round(v, 4) for k, v in COST_BY_MODEL.items()},
        "pending_questions": pending_q,
        "report_count": len(REPORTS),
        "activity_count": len(ACTIVITY),
        "pending_requirements": pending_req,
        "backlog_count": len(BACKLOG),
    }


@app.get("/api/states")
def states():
    return {"states": STATES}


@app.post("/api/agents/{name}/state")
def set_state(name: str, update: StateUpdate):
    if name not in ROLE:
        raise HTTPException(404, f"unknown agent: {name}")
    prev = STATES.get(name, "idle")
    STATES[name] = update.state
    if prev != update.state:
        log_event(name, "state", f"{prev} → {update.state}")
        # Accrue tier-aware cost when agent transitions INTO working
        if update.state == "working":
            _accrue_for_state_working(name)
    return {"name": name, "state": update.state}


# ── Activity log ─────────────────────────────────────────────────────
@app.get("/api/activity")
def get_activity(limit: int = 80):
    # Newest first
    items = list(ACTIVITY)
    items.reverse()
    return {"events": items[:limit], "total": len(ACTIVITY)}


@app.post("/api/activity")
def post_activity(ev: ActivityEvent):
    evt = log_event(ev.agent, ev.kind, ev.detail)
    # Smaller follow-up accrual for tool usage on tier-3 members
    if ev.kind == "tool" and ev.agent in ROLE and _tier_of(ev.agent) == 3:
        accrue_cost(ev.agent, 150, 100)
    return evt


# ── Questions ────────────────────────────────────────────────────────
@app.get("/api/questions")
def list_questions():
    return {"questions": QUESTIONS}


@app.post("/api/questions")
def create_question(q: QuestionIn):
    if q.agent not in ROLE:
        raise HTTPException(404, f"unknown agent: {q.agent}")
    qid = str(uuid.uuid4())[:8]
    item = {
        "id": qid,
        "agent": q.agent,
        "raw": q.raw,
        "translated": None,
        "answer": None,
        "context": q.context,
        "status": "pending_translation",  # → pending_user → answered
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
            q["status"] = "answered"
            q["answered"] = now_iso()
            log_event(q["agent"], "question", f"사용자 답변 수신({qid})")
            return q
    raise HTTPException(404, "question not found")


# ── Reports ──────────────────────────────────────────────────────────
@app.get("/api/reports")
def list_reports():
    # Newest first, without bodies
    summary = [
        {k: r[k] for k in ("id", "title", "author", "created")}
        for r in REPORTS
    ]
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
    item = {
        "id": rid,
        "title": r.title,
        "content_md": r.content_md,
        "author": r.author,
        "created": now_iso(),
    }
    REPORTS.insert(0, item)
    # Persist to disk
    fn = REPORTS_DIR / f"{item['created'].replace(':','-')}-{rid}.md"
    fn.write_text(f"# {r.title}\n\n_by {r.author} @ {item['created']}_\n\n{r.content_md}", encoding="utf-8")
    log_event(r.author, "report", f"보고서 발행: {r.title}")
    return item


# ── Mission (사훈) ───────────────────────────────────────────────────
def load_mission() -> dict:
    if MISSION_FILE.exists():
        try:
            import json
            return json.loads(MISSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(DEFAULT_MISSION)


def save_mission(m: dict) -> None:
    import json
    MISSION_FILE.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/api/mission")
def get_mission():
    return load_mission()


@app.post("/api/mission")
def set_mission(m: MissionIn):
    company = (m.company or "").strip()
    industry = m.industry.strip()
    philosophy = m.philosophy.strip()
    goal = m.goal.strip()
    data = {
        "company": company,
        "industry": industry,
        "philosophy": philosophy,
        "goal": goal,
        # company + industry + goal all required to exit placeholder state
        "placeholder": not (company and industry and goal),
    }
    save_mission(data)
    log_event("system", "mission", f"사훈 업데이트: {company} · {industry}")
    return data


@app.get("/api/guide/bedrock")
def get_bedrock_guide():
    """Return the Bedrock setup guide (ko + en) as structured sections."""
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
            {"h": "4. OmniHarness 와 연결",
             "body": "FabCanvas.ai 디렉토리 안에서 `claude` 를 실행하면 `.claude/settings.json` 에 정의된 훅이 OmniHarness 뷰어(:8081)로 에이전트 상태를 밀어 넣습니다. Bedrock 으로 운영하면 총괄(orchestrator)도 Bedrock Opus 로 돌게 됩니다."},
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
            {"h": "4. Wire into OmniHarness",
             "body": "Run `claude` inside the FabCanvas.ai directory; the hooks in `.claude/settings.json` will push agent state into the OmniHarness viewer (:8081). The orchestrator will then run on Bedrock Opus."},
            {"h": "Verification",
             "body": "`claude --version` works and answers a simple prompt. On error, first verify `aws bedrock list-foundation-models --region us-east-1` returns the models."},
        ],
    }


# ── Requirements (user → orchestrator) ───────────────────────────────
@app.get("/api/requirements")
def list_requirements():
    # Newest first
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


class RequirementStatus(BaseModel):
    status: Literal["new", "planning", "in_progress", "done", "cancelled"]


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
            # Only cancellable while not yet done
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


# ── Backlog (advanced view of upcoming tasks) ────────────────────────
BACKLOG_SEED: list[tuple[str, str]] = [
    ("feat-dashboard-filter",              "대시보드에 날짜범위 필터 추가"),
    ("fix-tracker-gantt-tooltip",          "Gantt bar hover 툴팁"),
    ("refactor-auth-session-ttl",          "세션 TTL 기본 30분으로"),
    ("feat-filebrowser-upload-progress",   "업로드 진행률 표시"),
    ("feat-admin-settings-audit-log",      "설정 변경 감사 로그"),
    ("chore-db-migration-tool",            "마이그레이션 CLI"),
    ("feat-tracker-category-colors-import","카테고리 색상 CSV import"),
    ("feat-dashboard-export-png",          "차트 PNG 저장"),
    ("fix-splittable-race-condition",      "sticky header 1px gap"),
    ("feat-messages-typing-indicator",     "타이핑 중 표시"),
    ("feat-ml-job-queue",                  "ML 작업 큐 시각화"),
    ("feat-ettime-heatmap",                "시간대별 히트맵"),
    ("refactor-frontend-api-helper",       "sf() 에러 처리 일관화"),
    ("feat-admin-user-bulk-activate",      "대량 승인"),
    ("feat-home-version-diff",             "버전 변경점 펼치기"),
    ("security-audit-session-cookie",      "SameSite/secure 플래그"),
    ("feat-reformatter-schema-suggest",    "스키마 자동 추천"),
    ("chore-ci-type-check",                "tsc --noEmit CI"),
    ("feat-dbmap-graph-minimap",           "TableMap minimap"),
    ("feat-tracker-bulk-status-change",    "이슈 상태 일괄 변경"),
]


def seed_backlog() -> None:
    if BACKLOG:
        return
    rnd = random.Random(20260418)
    for slug, ko in BACKLOG_SEED:
        title = f"{slug}  {ko}"
        # Priority skewed to P1
        priority = rnd.choices(["P0", "P1", "P2"], weights=[0.15, 0.6, 0.25])[0]
        estimate = rnd.choice(["S", "M", "L"])
        s = slug.lower()
        if "gantt" in s or "tooltip" in s or "heatmap" in s or "minimap" in s or "version-diff" in s:
            team = "frontend"
        elif "auth" in s or "migration" in s or "schema" in s or "ml-job" in s:
            team = "backend"
        elif "audit" in s or "security" in s or "session-cookie" in s or "admin" in s:
            team = "mgmt"
        elif "ci-type" in s or "reformatter" in s:
            team = "eval"
        else:
            team = rnd.choice(["backend", "frontend", "mgmt", "eval"])
        BACKLOG.append({
            "id": slug,
            "title": title,
            "team": team,
            "priority": priority,
            "estimate": estimate,
            "status": "queued",
        })
    # Sprinkle a few non-queued statuses
    idxs = list(range(len(BACKLOG)))
    rnd.shuffle(idxs)
    planned_n = min(3, len(idxs))
    for i in idxs[:planned_n]:
        BACKLOG[i]["status"] = "planned"
    for i in idxs[planned_n:planned_n + rnd.choice([1, 2])]:
        BACKLOG[i]["status"] = "blocked"


seed_backlog()


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
    return {
        "ok": True,
        "templates_dir": str(TEMPLATES),
        "exists": TEMPLATES.exists(),
    }


# ── MCPs ─────────────────────────────────────────────────────────────
MCPS = [
    {
        "id": "filesystem",
        "name_ko": "파일시스템 MCP",
        "name_en": "Filesystem MCP",
        "purpose_ko": "프로젝트 파일을 안전하게 읽고 쓰기 위한 도구. 파일 목록, 원본 읽기, 텍스트 교체를 제공합니다.",
        "purpose_en": "Safely read and write project files. Provides list, read, and edit.",
        "icon_tile": "fridge",
    },
    {
        "id": "browser",
        "name_ko": "브라우저 MCP",
        "name_en": "Browser MCP",
        "purpose_ko": "웹 페이지를 열어 DOM을 조작하거나 스크린샷을 찍어 에이전트가 실제 화면을 확인하게 합니다.",
        "purpose_en": "Open pages, manipulate DOM, capture screenshots so agents can verify real UI.",
        "icon_tile": "water",
    },
    {
        "id": "shell",
        "name_ko": "Shell MCP",
        "name_en": "Shell MCP",
        "purpose_ko": "빌드/테스트/curl 같은 쉘 명령을 안전한 샌드박스 환경에서 실행합니다.",
        "purpose_en": "Run build/test/curl commands in a sandboxed shell.",
        "icon_tile": "coffee",
    },
    {
        "id": "github",
        "name_ko": "GitHub MCP",
        "name_en": "GitHub MCP",
        "purpose_ko": "PR/이슈 조회, 리뷰 코멘트 수집, 릴리즈 조회 등 깃허브 리포지토리와 상호작용합니다.",
        "purpose_en": "Interact with GitHub repos: PRs, issues, review comments, releases.",
        "icon_tile": "printer",
    },
    {
        "id": "memory",
        "name_ko": "Memory MCP",
        "name_en": "Memory MCP",
        "purpose_ko": "대화 간 오래 유지되어야 할 사용자/프로젝트 지식을 저장·조회합니다.",
        "purpose_en": "Store and retrieve long-lived user/project knowledge across sessions.",
        "icon_tile": "server",
    },
]


@app.get("/api/mcps")
def get_mcps():
    return {"mcps": MCPS}


# ── Org chart (hierarchical drill-down) ──────────────────────────────
ORG_HIERARCHY_LABELS: list[dict] = [
    {"id": "top",    "label_ko": "총괄",         "label_en": "Orchestrator"},
    {"id": "leads",  "label_ko": "팀 리드",       "label_en": "Team Leads"},
    {"id": "dev",    "label_ko": "개발팀",        "label_en": "Dev Team"},
    {"id": "domain", "label_ko": "도메인 전문",   "label_en": "Domain Specialists"},
    {"id": "mgmt",   "label_ko": "경영지원팀",    "label_en": "Management Support"},
    {"id": "eval",   "label_ko": "평가팀",        "label_en": "Evaluation"},
]


@app.get("/api/org")
def get_org():
    # Derive members dynamically so they stay in sync with ROLE + loaded agents
    loaded_names = {a["name"] for a in load_agents()}
    hierarchy = []
    for node in ORG_HIERARCHY_LABELS:
        tid = node["id"]
        members = [
            name
            for name, role in ROLE.items()
            if role[0] == tid and name in loaded_names
        ]
        hierarchy.append({
            "id": tid,
            "label_ko": node["label_ko"],
            "label_en": node["label_en"],
            "members": members,
        })
    return {"hierarchy": hierarchy}


# ── Providers (placeholder for future UI) ────────────────────────────
PROVIDERS = [
    {"id": "anthropic",        "name": "Anthropic Claude",       "models": ["opus", "sonnet", "haiku"], "enabled": True,
     "note_ko": "Anthropic 공식 API — Claude Code CLI 기본", "note_en": "Official Anthropic API — default for Claude Code CLI"},
    {"id": "bedrock",          "name": "Amazon Bedrock (Claude)", "models": ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"], "enabled": True,
     "note_ko": "AWS Bedrock 경유 Claude — 사내 AWS 계정에서 Claude CLI 동일하게 사용",
     "note_en": "Claude via AWS Bedrock — run Claude Code CLI through your corporate AWS account"},
    {"id": "google",           "name": "Google Gemini",           "models": ["gemini-pro", "nano-banana"], "enabled": False,
     "note_ko": "이미지/멀티모달 작업용 — 활성화 예정", "note_en": "For image/multimodal — planned"},
    {"id": "openai",           "name": "OpenAI",                  "models": ["gpt-4.1", "gpt-4o-mini"], "enabled": False,
     "note_ko": "텍스트 일반 — 활성화 예정", "note_en": "General text — planned"},
    {"id": "fal",              "name": "fal.ai",                  "models": ["flux-dev", "flux-pro"], "enabled": False,
     "note_ko": "이미지 생성 — 활성화 예정", "note_en": "Image generation — planned"},
]


@app.get("/api/providers")
def get_providers():
    return {"providers": PROVIDERS}


# ── Dormant sample data (kept for reference, not auto-inserted) ──────
SAMPLE_QUESTIONS = [
    {
        "agent": "be-dashboard",
        "raw": "ChartConfig.date_range 필드 추가 시 DB 마이그레이션 필요한가? legacy 차트들은 이 필드 없이 저장돼 있는데 코드에서 optional(default=None)으로 처리해도 될지 OR 마이그레이션 스크립트 작성 필요한지 결정 필요.",
    },
    {
        "agent": "be-tracker",
        "raw": "이슈 카테고리를 [{name,color}] 객체 배열로 보관하는데, 예전 차트 렌더에서는 카테고리별 색상을 해시로 자동 생성함. 새 색상 필드를 우선할지(사용자 지정 우선) 아니면 기존 해시를 폴백으로 유지할지.",
    },
    {
        "agent": "industry-researcher",
        "raw": "조사한 바로는 최근 Fab 용 툴들이 SPC + APC 통합을 기본 제공함. FabCanvas 에 APC(공정 자동 제어) 모듈을 신설 논의할지?",
    },
]


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
