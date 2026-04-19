"""OmniHarness active coordinator — state-transition playback engine.

The coordinator is **LLM-free**: it classifies the requirement text with a
small keyword heuristic, builds a linear plan of
``Step(agent, phase, detail, min_duration_s)`` entries, and walks the
plan as an asyncio task.  Each step mutates the in-process ``STATES`` /
``ACTIVITY`` / ``BACKLOG`` / ``REQUIREMENTS`` tables **directly** — no
HTTP round-trips — so the viewer sees the same transitions it would
from real Claude Code hook activity.

Two modes share this exact playback:

* Claude Code mode — the user's live session fires its own activity
  POSTs. The coordinator runs in parallel; if the external hook keeps
  a given agent ``working``, we extend its step timer rather than
  prematurely flipping back to ``idle``.
* Bedrock mode — no external hooks, so the coordinator is the *only*
  thing driving the viewer. Same plan, same transitions. A future
  executor can plug in next to the coordinator to actually invoke
  Bedrock.

Public surface used by ``app.py``:

* ``plan(requirement, roster) -> list[Step]``
* ``run_coordinator(rid)``            (async coroutine)
* ``start_coordinator(rid)``          creates + registers the task
* ``stop_coordinator(rid)``           cancels + unregisters
* ``list_coordinators()``             introspection for /api/coordinate
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal

# Imported lazily inside functions to avoid an import cycle at module
# load time — ``app.py`` imports this module at the top, and this module
# needs to read/write ``app.STATES`` etc.


Phase = Literal["start", "work", "done"]


@dataclass
class Step:
    agent: str
    phase: Phase
    detail: str
    min_duration_s: float = 2.0
    # 같은 group id 를 가진 steps 는 phase-wave 단위로 동시에 발사된다
    # (start wave 에서 모두 working 으로, done wave 에서 모두 idle 로).
    # None 이면 기존대로 단일 직렬 실행.
    group: int | None = None


@dataclass
class CoordState:
    rid: str
    # Either an asyncio.Task or our _FutureAdapter — only .cancel()/
    # .done() are read from app-side code.
    task: object
    started_at: float = field(default_factory=time.time)
    steps: list[Step] = field(default_factory=list)
    current_index: int = 0
    current_agent: str | None = None


COORDINATOR_TASKS: dict[str, CoordState] = {}


# ── Keyword heuristic ────────────────────────────────────────────────
# Each bucket maps to (dev/domain candidates, tail reviewers). We never
# invoke an agent outside the active roster — the caller filters.

_KW_UI = [
    "ui", "프론트", "화면", "디자인", "테이블", "차트", "로그인", "브랜드",
    "레이아웃", "대시보드", "dashboard", "색상", "테마", "폰트",
]
_KW_ML = [
    "ml", "shap", "모델", "예측", "분류", "학습", "추론",
    "regression", "classifier",
]
_KW_API = [
    "api", "엔드포인트", "백엔드", "라우터", "스키마", "endpoint", "schema",
    "route", "handler",
]
_KW_DOMAIN = [
    "도메인", "공정", "sti", "gate", "beol", "area", "feol", "cmp",
    "wafer", "lot", "recipe",
]


def _match(text: str, kws: list[str]) -> bool:
    t = (text or "").lower()
    return any(k in t for k in kws)


def _pick_feature_tags(text: str) -> list[str]:
    """Detect FabCanvas feature tags from the requirement text.

    After the 2026-04-19 slim, there are no dev-* fan-out agents any more —
    dev-lead is a single full-stack worker. We only keep the keyword → tag
    mapping so the activity-log renderer can badge dev-lead's work with
    which feature(s) it touched (dashboard / spc / ml / …). Order is most-
    specific first, and a single requirement can legitimately hit multiple
    tags.
    """
    t = (text or "").lower()
    table = [
        (["dashboard", "대시보드"],       "dashboard"),
        (["table", "테이블"],             "tablemap"),
        (["admin", "관리자", "브랜드"],   "admin"),
        (["spc", "관리도"],               "spc"),
        (["wafer", "웨이퍼"],              "wafer-map"),
        (["ettime", "eng-time"],          "ettime"),
        (["tracker", "추적"],             "tracker"),
        (["file", "browser", "파일"],     "filebrowser"),
        (["messages", "메시지", "알림"],  "messages"),
        (["ml"],                          "ml"),
    ]
    tags: list[str] = []
    for kws, tag in table:
        if any(k in t for k in kws) and tag not in tags:
            tags.append(tag)
    return tags


def _in_roster(name: str, roster: set[str]) -> bool:
    return name in roster


def plan(requirement: dict, roster: list[str]) -> list[Step]:
    """Build a linear Step sequence from the requirement text.

    Post-2026-04-19 slim: the roster is 8 agents (orchestrator + dev-lead
    + 6 reviewers). Domain-rules live under `projects/<proj>/knowledge/`
    and are not agents, so they don't appear in the wave. We still pick
    feature tags from the text (dashboard / spc / ml / …) so dev-lead's
    activity detail badges which FabCanvas feature the work touched.
    """
    text = str(requirement.get("text") or "")
    rset = set(roster)
    steps: list[Step] = []

    tags = _pick_feature_tags(text)
    tag_str = "+".join(tags) if tags else "일반"

    # orchestrator dispatch (router only — heavy deliberation happens in
    # dev-lead, reviewers react afterwards).
    steps.append(Step("orchestrator", "start",
                      f"요구사항 수신 · dev-lead 배정 [{tag_str}]: {text[:50]}", 1.0))

    # dev wave and review wave share one group so they fire in parallel
    # — dev-lead implements while reviewers warm up and run checks.
    active_group = 5

    # Route by bucket, but we always end up calling dev-lead (no fan-out).
    if _match(text, _KW_DOMAIN):
        work_detail = f"도메인 판단 — knowledge md 참조 ({tag_str})"
    elif _match(text, _KW_ML):
        work_detail = f"ML 파이프라인 구현 ({tag_str})"
    elif _match(text, _KW_API):
        work_detail = f"백엔드 라우터/스키마 변경 ({tag_str})"
    elif _match(text, _KW_UI):
        work_detail = f"프론트엔드 화면/스타일 변경 ({tag_str})"
    else:
        work_detail = f"요구사항 구현 ({tag_str})"

    if _in_roster("dev-lead", rset):
        steps.append(Step("dev-lead", "start", f"작업 착수 [{tag_str}]", 1.5, group=active_group))
        steps.append(Step("dev-lead", "work",  work_detail,                3.0, group=active_group))
        steps.append(Step("dev-lead", "done",  f"구현 완료 [{tag_str}]",  0.5, group=active_group))

    # Reviewer wave — orchestrator picks which reviewers fire based on
    # bucket. ux-reviewer for UI, security-auditor for API/admin, etc.
    # All fire in the same group for parallel lighting.
    review_pool: list[tuple[str, str, str]] = []
    if _match(text, _KW_UI):
        review_pool.append(("ux-reviewer", "가시성/일관성/정보 위계 점검", "UX 리뷰 완료"))
    if _match(text, _KW_API) or "admin" in tags:
        review_pool.append(("security-auditor", "권한/경로/의존성 감사", "보안 점검 완료"))
    review_pool.append(("dev-verifier", "스펙 대비 빌드/엔드포인트 검증", "검증 완료"))
    if any(t in tags for t in ("admin",)):
        review_pool.append(("admin-role-tester", "관리자 라이프사이클 시나리오", "관리자 검증 완료"))
    else:
        review_pool.append(("user-role-tester", "유저 시나리오 실행", "사용성 검증 완료"))
    if _match(text, _KW_DOMAIN):
        review_pool.append(("domain-researcher", "업계/학계 자료 조사", "조사 완료"))

    for reviewer, detail_w, detail_d in review_pool:
        if _in_roster(reviewer, rset):
            steps.append(Step(reviewer, "start", f"{reviewer} 시작", 1.5, group=active_group))
            steps.append(Step(reviewer, "work",  detail_w,            2.0, group=active_group))
            steps.append(Step(reviewer, "done",  detail_d,            0.5, group=active_group))

    steps.append(Step("orchestrator", "done", f"요구사항 완료 [{tag_str}]", 0.5))
    return steps


# ── Runtime ─────────────────────────────────────────────────────────

def _last_activity_ts_for(agent: str) -> float | None:
    """Return last activity wall-clock ts for ``agent`` or None."""
    import app as backend  # late-import to dodge circular at load time
    for ev in reversed(backend.ACTIVITY):
        if ev.get("agent") == agent:
            # event ts is an iso string — parse lightly to epoch.
            s = ev.get("ts") or ""
            try:
                return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%S"))
            except Exception:
                return None
    return None


def _set_state(agent: str, state: str) -> None:
    """Mutate backend.STATES and log a state-transition event."""
    import app as backend
    roster = set(backend.current_roster())
    if agent not in roster:
        return
    prev = backend.STATES.get(agent, "idle")
    if prev == state:
        return
    backend.STATES[agent] = state
    backend.log_event(agent, "state", f"{prev} → {state}")
    if state == "working":
        backend._accrue_for_state_working(agent)


def _log_activity(agent: str, kind: str, detail: str) -> None:
    import app as backend
    roster = set(backend.current_roster())
    if agent in roster or agent == "system":
        backend.log_event(agent, kind, detail)


def _update_req(rid: str, status: str) -> None:
    import app as backend
    _req_to_backlog = {
        "planning":    "planning",
        "in_progress": "working",
        "done":        "done",
        "cancelled":   "cancelled",
    }
    for item in backend.REQUIREMENTS:
        if item["id"] == rid:
            prev = item.get("status")
            if prev == status:
                return
            item["status"] = status
            backend.log_event(
                item.get("assigned_to") or "orchestrator",
                "requirement",
                f"요구사항 상태 {prev} → {status}",
            )
            bstatus = _req_to_backlog.get(status)
            if bstatus:
                for b in backend.BACKLOG:
                    if b.get("source_req_id") == rid:
                        b["status"] = bstatus
            backend._save_state()
            return


def _get_req(rid: str) -> dict | None:
    import app as backend
    for item in backend.REQUIREMENTS:
        if item["id"] == rid:
            return item
    return None


_PHASE_ORDER = {"start": 0, "work": 1, "done": 2}


def _build_waves(steps: list[Step]) -> list[list[Step]]:
    """연속된 group 동일 steps 를 phase 별 wave 로 묶는다.

    결과 리스트의 각 원소는 "동시에 실행될 steps" — group=None 이면 1개짜리 wave,
    group 이 있으면 해당 그룹 내에서 phase 별로 (start wave · work wave · done wave)
    로 쪼개 각 wave 는 병렬 발사 가능.
    """
    waves: list[list[Step]] = []
    i = 0
    while i < len(steps):
        s = steps[i]
        if s.group is None:
            waves.append([s])
            i += 1
            continue
        gid = s.group
        block: list[Step] = []
        while i < len(steps) and steps[i].group == gid:
            block.append(steps[i])
            i += 1
        # phase 별로 묶어 wave 로 만든다 (start → work → done 순).
        by_phase: dict[str, list[Step]] = {"start": [], "work": [], "done": []}
        for b in block:
            by_phase.setdefault(b.phase, []).append(b)
        for phase in ("start", "work", "done"):
            if by_phase[phase]:
                waves.append(by_phase[phase])
    return waves


async def _sleep_step(step: Step, hold_until: float) -> None:
    """Sleep at least ``step.min_duration_s`` from now, and extend if a
    parallel hook keeps bumping this agent's activity timestamp."""
    # Baseline wait first so the viewer has time to paint.
    await asyncio.sleep(step.min_duration_s)
    # Heuristic extension: if the agent has had activity within the last
    # 2s (likely from a live Claude Code hook), extend by another second
    # up to a small cap to avoid blocking forever.
    extended = 0.0
    while extended < 6.0:
        ts = _last_activity_ts_for(step.agent)
        if ts is None:
            break
        gap = time.time() - ts
        if gap > 2.0:
            break
        await asyncio.sleep(1.0)
        extended += 1.0


async def run_coordinator(rid: str) -> None:
    """Walk the plan for ``rid`` until done or cancelled."""
    import app as backend  # noqa: F401 — ensures module is importable
    req = _get_req(rid)
    if req is None:
        return
    roster = backend.current_roster()
    steps = plan(req, roster)
    reg = COORDINATOR_TASKS.get(rid)
    if reg:
        reg.steps = steps
    print(f"[coord] rid={rid} plan_len={len(steps)} agent0={steps[0].agent if steps else '-'}")
    # Enter planning → in_progress quickly so the backlog reflects motion.
    _update_req(rid, "planning")
    await asyncio.sleep(0.5)
    _update_req(rid, "in_progress")

    # Wave 단위 실행: group 이 같은 연속 steps 을 phase 별로 묶어 동시에 발사.
    # group=None 인 step 은 그대로 단일 실행.
    waves = _build_waves(steps)

    try:
        for wi, wave in enumerate(waves):
            cur = _get_req(rid)
            if cur is None or cur.get("status") == "cancelled":
                print(f"[coord] rid={rid} cancelled at wave={wi}")
                return
            reg = COORDINATOR_TASKS.get(rid)
            if reg:
                reg.current_index = wi
                reg.current_agent = (
                    ",".join(sorted({s.agent for s in wave})) if len(wave) > 1
                    else wave[0].agent
                )

            # 같은 wave 안에서는 모든 step 을 동시에 apply.
            for step in wave:
                if step.phase == "start":
                    _set_state(step.agent, "working")
                    _log_activity(step.agent, "coord", step.detail)
                elif step.phase == "work":
                    _set_state(step.agent, "working")
                    _log_activity(step.agent, "tool", step.detail)
                elif step.phase == "done":
                    _log_activity(step.agent, "coord", step.detail)
                    _set_state(step.agent, "idle")

            max_dur = max(s.min_duration_s for s in wave)
            await asyncio.sleep(max_dur)
            # 동일 에이전트 라이브 활동 감지 시 확장 (첫 step 기준으로 heuristic 동일 적용)
            anchor = wave[0]
            extended = 0.0
            while extended < 6.0:
                ts = _last_activity_ts_for(anchor.agent)
                if ts is None:
                    break
                gap = time.time() - ts
                if gap > 2.0:
                    break
                await asyncio.sleep(1.0)
                extended += 1.0
            await asyncio.sleep(1.2)

        _update_req(rid, "done")
        print(f"[coord] rid={rid} DONE ({len(waves)} waves)")
        # Notify app so it can bump COORDINATOR_COMPLETED and, every
        # OMNI_AUDIT_EVERY runs, kick off an audit pass.
        try:
            import app as backend
            hook = getattr(backend, "on_coordinator_complete", None)
            if callable(hook):
                hook(rid)
        except Exception as _hook_exc:
            print(f"[coord] rid={rid} audit hook skipped: {_hook_exc}")
    except asyncio.CancelledError:
        print(f"[coord] rid={rid} task cancelled")
        raise
    finally:
        # Leave all step agents idle regardless of how we exited.
        touched = {s.agent for s in steps}
        for a in touched:
            try:
                _set_state(a, "idle")
            except Exception:
                pass
        COORDINATOR_TASKS.pop(rid, None)


def start_coordinator(rid: str) -> bool:
    """Register and start a coordinator task for ``rid``. Returns False
    if one is already running for this requirement.

    Called from FastAPI sync endpoints, which run in a threadpool — so
    there's no running loop on *this* thread. We grab the main
    application loop via ``_get_main_loop()`` (stashed at startup) and
    schedule the coroutine there with ``run_coroutine_threadsafe``.
    """
    if rid in COORDINATOR_TASKS:
        return False
    loop = _MAIN_LOOP
    if loop is None:
        # Fallback — try to find a running loop; this will succeed when
        # called from an async context (e.g. an async endpoint).
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

    # If we're *on* the loop already, create_task is fine; otherwise we
    # need the threadsafe variant and then adapt the concurrent.futures
    # Future into an asyncio.Task-like handle (we only need .cancel /
    # .done for our state bookkeeping).
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is loop:
        task = loop.create_task(run_coordinator(rid))
    else:
        fut = asyncio.run_coroutine_threadsafe(run_coordinator(rid), loop)
        task = _FutureAdapter(fut)
    COORDINATOR_TASKS[rid] = CoordState(rid=rid, task=task)
    return True


# ── Main-loop capture + threadsafe future adapter ──────────────────
_MAIN_LOOP: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called once from app startup to capture the running loop so
    sync endpoints can schedule coroutines on it."""
    global _MAIN_LOOP
    _MAIN_LOOP = loop


class _FutureAdapter:
    """Minimal shim so a concurrent.futures.Future returned by
    ``run_coroutine_threadsafe`` quacks like the ``asyncio.Task`` we
    stash in :class:`CoordState`. Only ``cancel`` / ``done`` are used
    by the coordinator registry."""

    def __init__(self, fut):
        self._fut = fut

    def cancel(self) -> bool:
        return self._fut.cancel()

    def done(self) -> bool:
        return self._fut.done()


def stop_coordinator(rid: str) -> bool:
    reg = COORDINATOR_TASKS.get(rid)
    if not reg:
        return False
    reg.task.cancel()
    COORDINATOR_TASKS.pop(rid, None)
    return True


def list_coordinators() -> list[dict]:
    out = []
    for rid, reg in COORDINATOR_TASKS.items():
        out.append({
            "rid": rid,
            "current_step_index": reg.current_index,
            "current_agent": reg.current_agent,
            "started_at": reg.started_at,
            "steps_total": len(reg.steps),
            "done": reg.task.done(),
        })
    return out


# ── Optional LLM-refinement hook (future) ───────────────────────────
# When CLAUDE_CODE_USE_BEDROCK=1 (or ANTHROPIC_API_KEY) is set we could
# ask the LLM to refine the heuristic plan — e.g. pick agents more
# accurately or rewrite the step detail strings into the project's voice.
# TODO: wire _call_bedrock / _call_anthropic here. Intentionally not
# implemented so this module stays LLM-free by default and usable in
# air-gapped setups.
