"""OmniHarness Viewer — FastAPI backend (v0.3).

Endpoints:
- GET  /api/topology           org chart + per-agent state + demo flag
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

- POST /api/demo               toggle simulated activity cycler

- /                            serves the Vite-built SPA from ../frontend/dist

Run: cd OmniHarness/backend && uvicorn app:app --host 0.0.0.0 --port 8081
"""
from __future__ import annotations

import asyncio
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
    "industry": "",
    "philosophy": "",
    "goal": "",
    "placeholder": True,
}

# ── Org chart ────────────────────────────────────────────────────────
ROLE = {
    "orchestrator":        ("top",      "fox",     "🦊", "#E87722"),
    "dev-lead":            ("leads",    "bear",    "🐻", "#8B5A2B"),
    "mgmt-lead":           ("leads",    "bear",    "🐻", "#8B5A2B"),
    "eval-lead":           ("leads",    "bear",    "🐻", "#8B5A2B"),
    "be-dashboard":        ("backend",  "rabbit",  "🐰", "#F4B8B8"),
    "be-filebrowser":      ("backend",  "rabbit",  "🐰", "#F4B8B8"),
    "be-tracker":          ("backend",  "rabbit",  "🐰", "#F4B8B8"),
    "fe-dashboard":        ("frontend", "rabbit",  "🐰", "#B8D0F4"),
    "fe-filebrowser":      ("frontend", "rabbit",  "🐰", "#B8D0F4"),
    "fe-tracker":          ("frontend", "rabbit",  "🐰", "#B8D0F4"),
    "reporter":            ("mgmt",     "raccoon", "🦝", "#7A5F47"),
    "hr":                  ("mgmt",     "owl",     "🦉", "#5C3E2A"),
    "ux-reviewer":         ("eval",     "badger",  "🦡", "#6C6C6C"),
    "dev-verifier":        ("eval",     "badger",  "🦡", "#6C6C6C"),
    "user-tester":         ("eval",     "badger",  "🦡", "#6C6C6C"),
    "admin-tester":        ("eval",     "badger",  "🦡", "#6C6C6C"),
    "feature-auditor":     ("eval",     "badger",  "🦡", "#6C6C6C"),
    "industry-researcher": ("eval",     "badger",  "🦡", "#6C6C6C"),
}

TEAMS = [
    {"id": "top",      "label": "총괄"},
    {"id": "leads",    "label": "팀 리드"},
    {"id": "backend",  "label": "개발1팀 Backend"},
    {"id": "frontend", "label": "개발2팀 Frontend"},
    {"id": "mgmt",     "label": "경영지원팀"},
    {"id": "eval",     "label": "평가팀"},
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
# Default OFF: the viewer starts quiet and only lights up for REAL work pushed
# through hooks (FabCanvas.ai/.claude/settings.json → /api/agents/{name}/state).
# The user can toggle DEMO=ON from the UI to see simulated activity.
DEMO_ENABLED: bool = False

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

# ── Models ───────────────────────────────────────────────────────────
class StateUpdate(BaseModel):
    state: State


class DemoToggle(BaseModel):
    enabled: bool


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
    industry: str
    philosophy: str
    goal: str


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


def model_of(agent_name: str) -> str:
    # Infer model from org chart tier
    team = ROLE.get(agent_name, ("misc",))[0]
    return "opus" if team in ("top", "leads") else "sonnet"


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
    return {
        "agents": agents,
        "teams": teams,
        "total": len(agents),
        "demo": DEMO_ENABLED,
        "cost_total": round(COST_TOTAL, 4),
        "cost_by_model": {k: round(v, 4) for k, v in COST_BY_MODEL.items()},
        "pending_questions": pending_q,
        "report_count": len(REPORTS),
        "activity_count": len(ACTIVITY),
    }


@app.get("/api/states")
def states():
    return {"states": STATES, "demo": DEMO_ENABLED}


@app.post("/api/agents/{name}/state")
def set_state(name: str, update: StateUpdate):
    if name not in ROLE:
        raise HTTPException(404, f"unknown agent: {name}")
    prev = STATES.get(name, "idle")
    STATES[name] = update.state
    if prev != update.state:
        log_event(name, "state", f"{prev} → {update.state}")
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
    data = {
        "industry": m.industry.strip(),
        "philosophy": m.philosophy.strip(),
        "goal": m.goal.strip(),
        "placeholder": not (m.industry.strip() or m.philosophy.strip() or m.goal.strip()),
    }
    save_mission(data)
    log_event("system", "mission", "사훈 업데이트됨")
    return data


# ── Cost ─────────────────────────────────────────────────────────────
@app.get("/api/cost")
def get_cost():
    return {
        "total": round(COST_TOTAL, 4),
        "by_model": {k: round(v, 4) for k, v in COST_BY_MODEL.items()},
        "tokens_by_model": TOKENS_BY_MODEL,
    }


# ── Demo / Health ────────────────────────────────────────────────────
@app.post("/api/demo")
def toggle_demo(t: DemoToggle):
    global DEMO_ENABLED
    DEMO_ENABLED = t.enabled
    if not t.enabled:
        STATES.clear()
    log_event("system", "demo", f"demo mode: {'ON' if t.enabled else 'OFF'}")
    return {"demo": DEMO_ENABLED}


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "templates_dir": str(TEMPLATES),
        "exists": TEMPLATES.exists(),
        "demo": DEMO_ENABLED,
    }


# ── Demo data seeds ──────────────────────────────────────────────────
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


# ── Demo activity cycler ─────────────────────────────────────────────
async def demo_cycler():
    random.seed()
    tick = 0
    while True:
        try:
            await asyncio.sleep(2.0)
            tick += 1
            if not DEMO_ENABLED:
                continue

            agent_names = list(ROLE.keys())
            changed: list[tuple[str, str, str]] = []
            for _ in range(random.randint(1, 3)):
                name = random.choice(agent_names)
                cur = STATES.get(name, "idle")
                team = ROLE[name][0]
                if cur == "idle":
                    nxt = (
                        random.choice(["working", "waiting"])
                        if team in ("top", "leads")
                        else random.choices(
                            ["working", "waiting", "idle"],
                            weights=[0.3, 0.5, 0.2],
                        )[0]
                    )
                elif cur == "waiting":
                    nxt = random.choices(
                        ["working", "waiting", "idle"],
                        weights=[0.55, 0.3, 0.15],
                    )[0]
                else:  # working
                    nxt = random.choices(["working", "idle"], weights=[0.55, 0.45])[0]
                if cur != nxt:
                    STATES[name] = nxt
                    changed.append((name, cur, nxt))

            # 40% chance to nudge orchestrator
            if random.random() < 0.4:
                nxt = random.choice(["working", "waiting"])
                if STATES.get("orchestrator") != nxt:
                    prev = STATES.get("orchestrator", "idle")
                    STATES["orchestrator"] = nxt
                    changed.append(("orchestrator", prev, nxt))

            # Emit activity events + accrue cost for each working agent
            for agent in agent_names:
                if STATES.get(agent) == "working":
                    # Rough simulation: each working tick ~ 800 in / 350 out tokens
                    accrue_cost(agent, 800, 350)

            for name, prev, nxt in changed:
                if nxt == "working":
                    verb = random.choice([
                        "작업 착수", "파일 수정 시작", "엔드포인트 구현 중",
                        "리뷰 진행", "쿼리 최적화 중", "Gantt 렌더 수정 중",
                    ])
                    log_event(name, "state", f"⚡ {verb}")
                elif nxt == "waiting":
                    log_event(name, "state", "⏳ 다른 팀 결과 대기")
                else:
                    log_event(name, "state", "💤 대기 복귀")

            # Every ~8 ticks, create a sample question if fewer than 3 pending
            pending = sum(1 for q in QUESTIONS if q["status"] in ("pending_translation", "pending_user"))
            if tick % 8 == 3 and pending < 3 and SAMPLE_QUESTIONS:
                sample = SAMPLE_QUESTIONS[tick // 8 % len(SAMPLE_QUESTIONS)]
                # Agent creates question
                qid = str(uuid.uuid4())[:8]
                QUESTIONS.insert(0, {
                    "id": qid, "agent": sample["agent"],
                    "raw": sample["raw"], "translated": None, "answer": None,
                    "context": None, "status": "pending_translation",
                    "created": now_iso(), "answered": None,
                })
                log_event(sample["agent"], "question", "질문 제기: " + sample["raw"][:48])
                # mgmt-lead auto-translates after a moment (still needs user answer)
                await asyncio.sleep(0.8)
                translations = {
                    "be-dashboard": "대시보드 차트에 날짜 범위 필터를 추가하려고 하는데, 기존 차트들은 이 필드를 갖고 있지 않아요. (A) 기본값 None 으로 자동 적용할지 (B) 예전 차트들도 일괄 변환할지 골라주세요.",
                    "be-tracker":   "이슈 카테고리에 색상을 지정할 수 있게 되는데, 사용자가 색을 지정 안 하면 (A) 자동 색상(기존 방식) vs (B) 고정 회색 중 어느 쪽으로 보여줄지 골라주세요.",
                    "industry-researcher": "최근 반도체 Fab IT 툴들이 'APC(공정 자동 제어)' 모듈을 기본 제공하는 추세예요. FabCanvas 에 APC 신규 기능 검토를 시작할까요? (Yes / Later / No)",
                }
                for q in QUESTIONS:
                    if q["id"] == qid:
                        q["translated"] = translations.get(sample["agent"], sample["raw"])
                        q["status"] = "pending_user"
                        log_event("mgmt-lead", "question", f"질문 번역({qid})")
                        break

            # Every ~25 ticks, auto-generate a report if meaningful activity accumulated
            if tick % 25 == 7 and len(ACTIVITY) > 15:
                recent = list(ACTIVITY)[-40:]
                state_events = [e for e in recent if e["kind"] == "state"]
                q_events = [e for e in recent if e["kind"] == "question"]
                lines = ["## 이번 주기 주요 변경점\n"]
                if state_events:
                    lines.append(f"- 에이전트 상태 전이 **{len(state_events)}회** — 개발팀과 평가팀이 활발히 핑퐁 중이었어요.")
                working_names = [a for a, s in STATES.items() if s == "working"]
                if working_names:
                    lines.append(f"- 지금 작업 중인 에이전트: `" + ", ".join(working_names[:6]) + "`")
                if q_events:
                    lines.append(f"- 사용자에게 도움을 청하는 질문 **{len(q_events)}건** 누적.")
                lines.append(f"- 누적 API 비용: **${COST_TOTAL:.4f}** (이 중 opus ${COST_BY_MODEL['opus']:.4f} / sonnet ${COST_BY_MODEL['sonnet']:.4f}).")
                lines.append("\n## 사용자에게 드리는 한 줄 메시지\n")
                lines.append("> 요청하신 기능들이 순조롭게 진행 중입니다. 아래 질문 패널에 답만 주시면 막혀있던 작업이 풀립니다.")
                body_md = "\n".join(lines)
                rid = str(uuid.uuid4())[:8]
                REPORTS.insert(0, {
                    "id": rid,
                    "title": f"주기 보고서 #{len(REPORTS)+1}",
                    "content_md": body_md,
                    "author": "reporter",
                    "created": now_iso(),
                })
                try:
                    fn = REPORTS_DIR / f"auto-{rid}.md"
                    fn.write_text(f"# 주기 보고서 #{len(REPORTS)}\n\n_by reporter @ {now_iso()}_\n\n{body_md}", encoding="utf-8")
                except Exception:
                    pass
                log_event("reporter", "report", f"자동 보고서 발행 #{len(REPORTS)}")

        except Exception as e:
            # never let the cycler die on transient errors
            try:
                log_event("system", "error", f"cycler: {e}")
            except Exception:
                pass


@app.on_event("startup")
async def _boot():
    log_event("system", "boot", "OmniHarness Viewer 가동 — 실제 작업 대기 중")
    asyncio.create_task(demo_cycler())


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
