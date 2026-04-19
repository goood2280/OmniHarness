"""OmniHarness periodic audit pass.

Triggered every ``OMNI_AUDIT_EVERY`` coordinator completions (default 5),
or on demand via ``POST /api/audit/run``. The audit inspects recent
per-agent activity + cumulative COST_BY_AGENT and produces advisory
EVOLUTION proposals in three shapes:

* ``split_agent``  — agent whose avg working → idle span > SLOW_WORKING_S
* ``retire_agent`` — agent with zero calls in the last IDLE_RUNS_N
                     coordinator runs
* ``parallelize``  — two agents that always run sequentially and could
                     be fanned out in the same wave

Kept deliberately lightweight (pure stdlib, single async entrypoint) so
it can run side-by-side with a live coordinator without stealing the
event loop. Heavy analysis is synchronous but short (O(ACTIVITY)).

Integration points in ``app.py``:

* ``add_audit_proposal(item)`` — direct append to ``EVOLUTION`` so we
  bypass the strict ``EvolutionIn`` Pydantic model (which only knows the
  ``new_agent/feature/refactor/retire_agent`` kinds used elsewhere).
* ``STATES`` / ``log_event`` — viewer gets ``hr`` working → idle blinks
  while the audit runs, so the office floor-plan shows the activity.
* ``REPORTS`` — after each pass, security-auditor + reporter jointly
  publish a user-friendly digest of the proposals (build_audit_report).
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections import Counter, defaultdict
from typing import Iterable


# ── Tunables ────────────────────────────────────────────────────────
SLOW_WORKING_S = float(os.environ.get("OMNI_AUDIT_SLOW_S", "15"))
IDLE_RUNS_N = int(os.environ.get("OMNI_AUDIT_IDLE_RUNS", "20"))
PARALLEL_MIN_COOCCURRENCE = int(os.environ.get("OMNI_AUDIT_PARALLEL_MIN", "3"))


# ── Public state (read by /api/audit/status) ────────────────────────
LAST_AUDIT_AT: str | None = None
AUDIT_COUNT: int = 0

# Big-picture security pass — fires every BIG_SECURITY_EVERY coordinator
# completions from app.on_coordinator_complete (independent of the
# per-change security-auditor already on the review wave).
LAST_BIG_SECURITY_AT: str | None = None
BIG_SECURITY_COUNT: int = 0

# Sensitive-path substrings that bump the risk surface of a big-picture
# pass. Kept as plain substrings so we can match Windows/posix paths
# without importing pathspec. Add more here as the codebase grows.
_SENSITIVE_PATH_HINTS = (
    "backend/routers/",
    "backend\\routers\\",
    "core/",
    "core\\",
)
_CONFIG_FILE_HINTS = (
    ".dvc",              # DVC rule/pipeline files
    "dvc.yaml",
    "dvc.lock",
    ".env",
    "settings.py",
    "config.py",
    "permissions",
    "roles.json",
)


# ── Helpers ─────────────────────────────────────────────────────────
def _parse_ts(s: str) -> float | None:
    try:
        return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None


def _iter_activity() -> list[dict]:
    import app as backend
    return list(backend.ACTIVITY)


def _avg_working_spans(activity: list[dict]) -> dict[str, float]:
    """For each agent, mean seconds between 'working' entry and the next
    'idle' transition on that same agent. State-transition events are
    logged as ``kind='state'`` with detail like ``"idle → working"``.
    """
    pending_start: dict[str, float] = {}
    spans: dict[str, list[float]] = defaultdict(list)
    for ev in activity:
        if ev.get("kind") != "state":
            continue
        agent = ev.get("agent") or ""
        detail = ev.get("detail") or ""
        ts = _parse_ts(ev.get("ts") or "")
        if ts is None:
            continue
        if "→ working" in detail:
            pending_start[agent] = ts
        elif "→ idle" in detail:
            start = pending_start.pop(agent, None)
            if start is not None and ts >= start:
                spans[agent].append(ts - start)
    return {a: (sum(v) / len(v)) for a, v in spans.items() if v}


def _coordinator_runs(activity: list[dict]) -> list[dict]:
    """Each 'orchestrator' entry with kind='coord' and detail starting
    with '요구사항 수신' marks a coordinator run start; 'requirement 상태
    in_progress → done' marks its end. We return a list of per-run
    slices for co-occurrence analysis.
    """
    runs: list[dict] = []
    cur: dict | None = None
    for ev in activity:
        kind = ev.get("kind")
        agent = ev.get("agent")
        detail = ev.get("detail") or ""
        if agent == "orchestrator" and kind == "coord" and detail.startswith("요구사항 수신"):
            if cur is not None:
                runs.append(cur)
            cur = {"agents": set(), "order": []}
        if cur is not None:
            a = agent or ""
            if a and a != "system" and a != "user":
                cur["agents"].add(a)
                if a not in cur["order"]:
                    cur["order"].append(a)
            if kind == "requirement" and "→ done" in detail:
                runs.append(cur)
                cur = None
    if cur is not None:
        runs.append(cur)
    return runs


def _parallelizable_pairs(runs: list[dict]) -> list[tuple[str, str]]:
    """Heuristic: agents a, b that co-occurred in ≥ PARALLEL_MIN_COOCCURRENCE
    runs but were *always* ordered sequentially (a strictly before b or
    vice-versa) are candidates for wave-level parallelism.
    """
    cooccur: dict[tuple[str, str], int] = defaultdict(int)
    a_before_b: dict[tuple[str, str], int] = defaultdict(int)
    for run in runs:
        order = run.get("order") or []
        for i, a in enumerate(order):
            for b in order[i + 1:]:
                if a == b:
                    continue
                key = tuple(sorted((a, b)))
                cooccur[key] += 1
                if a == key[0]:
                    a_before_b[key] += 1
                else:
                    a_before_b[key] -= 1
    pairs: list[tuple[str, str]] = []
    for key, n in cooccur.items():
        if n < PARALLEL_MIN_COOCCURRENCE:
            continue
        # Always-sequential iff |a_before_b| == n (every co-occurrence
        # in the same direction).
        if abs(a_before_b[key]) == n:
            pairs.append(key)
    return pairs


def _build_proposals(
    activity: list[dict],
    cost_by_agent: dict,
    known_agents: Iterable[str],
) -> list[dict]:
    spans = _avg_working_spans(activity)
    runs = _coordinator_runs(activity)
    recent_runs = runs[-IDLE_RUNS_N:]
    active_in_window: set[str] = set()
    for r in recent_runs:
        active_in_window |= set(r.get("agents") or [])

    proposals: list[dict] = []

    # (1) Slow agents → split_agent
    for agent, avg_s in spans.items():
        if avg_s > SLOW_WORKING_S:
            proposals.append({
                "kind": "split_agent",
                "target": agent,
                "reason": (
                    f"평균 working 지속 {avg_s:.1f}s > {SLOW_WORKING_S:.0f}s — "
                    f"책임 분리로 wave 지연 축소 가능"
                ),
                "metric": {"avg_working_s": round(avg_s, 2)},
            })

    # (2) Under-utilized → retire_agent. Skip BASE roles that are always
    #     expected to be idle until summoned (hr, security-auditor, etc).
    import app as backend
    base = set(getattr(backend, "BASE_ROLES", {}).keys())
    for agent in known_agents:
        if agent in base:
            continue
        calls = int((cost_by_agent.get(agent) or {}).get("calls", 0))
        if agent in active_in_window:
            continue
        # Only suggest retire if the agent has zero recent runs *and*
        # has been seen before (calls > 0 historically) or is simply in
        # the roster but inert.
        if len(recent_runs) >= min(5, IDLE_RUNS_N):
            proposals.append({
                "kind": "retire_agent",
                "target": agent,
                "reason": (
                    f"최근 {len(recent_runs)} 코디네이터 런 중 호출 0회 "
                    f"(누적 calls={calls}) — 로스터에서 정리 검토"
                ),
                "metric": {
                    "recent_runs": len(recent_runs),
                    "total_calls": calls,
                },
            })

    # (3) Parallelizable pairs
    for (a, b) in _parallelizable_pairs(runs):
        proposals.append({
            "kind": "parallelize",
            "targets": [a, b],
            "reason": (
                f"{a} ↔ {b} 가 항상 순차로만 호출됨 "
                f"(≥{PARALLEL_MIN_COOCCURRENCE}회 공동 출현) — 동일 wave 로 병렬화 검토"
            ),
            "metric": {"a": a, "b": b},
        })

    return proposals


def _roster_names() -> list[str]:
    import app as backend
    try:
        return list(backend.current_roster())
    except Exception:
        return list(getattr(backend, "STATES", {}).keys())


# ── Direct EVOLUTION append (bypasses Pydantic EvolutionIn) ─────────
# Dedup window for audit-generated proposals. When an identical
# (kind, target, source) shape already has an ``accepted`` or ``rejected``
# record inside the last ``_EVO_DEDUP_DECIDED_WINDOW_S`` seconds we skip
# creating a new proposal — the user already decided on that exact
# finding and the audit pass would otherwise flood the roster tab with
# identical cards on every cycle.
_EVO_DEDUP_DECIDED_WINDOW_S = 24 * 3600  # 24 hours


def _normalize_target(target: str | list[str]) -> str:
    """Canonical target key used for dedup comparisons. Lists are
    sorted so that order doesn't create false-negatives (parallelize
    pairs ``(a,b)`` and ``(b,a)`` dedupe together)."""
    if isinstance(target, list):
        return " + ".join(sorted(str(x) for x in target))
    return str(target or "")


def _find_evolution_dup(kind: str, target_key: str, source: str) -> dict | None:
    """Return the most-recent EVOLUTION item matching the dedup key,
    or None. Matches on (kind, normalized target, source)."""
    import app as backend
    for item in backend.EVOLUTION:
        if item.get("kind") != kind:
            continue
        if item.get("source") != source:
            continue
        if _normalize_target(item.get("target") or "") != target_key:
            continue
        return item
    return None


def add_audit_proposal(kind: str, reason: str, target: str | list[str], metric: dict) -> dict:
    """Insert an audit-generated proposal into the EVOLUTION list.

    We bypass the /api/evolution POST handler because its pydantic model
    enforces a closed Literal for ``kind`` (new_agent/feature/refactor/
    retire_agent). Audit introduces ``split_agent`` and ``parallelize``
    in addition, which the viewer Evolution tab surfaces as advisory.

    Dedup guard:
      • If the same (kind, target, source='audit') is already
        ``status='proposed'`` — refresh its reason/metric in place and
        return the existing item. Avoids stacking identical cards.
      • If the same key is already ``accepted``/``rejected`` and was
        decided within 24h — skip and return the existing record.
      • Otherwise (decided long ago, same finding surfaced again) —
        create a fresh proposal.
    """
    import app as backend
    target_key = _normalize_target(target)
    existing = _find_evolution_dup(kind, target_key, source="audit")
    if existing is not None:
        status = existing.get("status")
        if status == "proposed":
            # Refresh the open proposal with the latest reason/metric so
            # the viewer reflects the most recent audit pass's finding.
            existing["reason"] = reason
            existing["rationale"] = reason
            payload = dict(existing.get("payload") or {})
            payload["metric"] = metric
            payload["target"] = target
            existing["payload"] = payload
            existing["created"] = backend.now_iso()
            return existing
        # Decided (accepted/rejected) — only re-raise after dedup window.
        decided_at = _parse_ts(existing.get("decided") or existing.get("created") or "")
        if decided_at is not None and (time.time() - decided_at) < _EVO_DEDUP_DECIDED_WINDOW_S:
            return existing

    eid = str(uuid.uuid4())[:8]
    if isinstance(target, list):
        title = f"[audit] {kind}: {' + '.join(target)}"
        target_val = " + ".join(target)
    else:
        title = f"[audit] {kind}: {target}"
        target_val = target
    item = {
        "id": eid,
        "agent": "hr",
        "kind": kind,
        "title": title,
        "rationale": reason,
        "reason": reason,           # audit convenience alias
        "target": target_val,       # audit convenience alias
        "payload": {"metric": metric, "target": target},
        "status": "proposed",
        "created": backend.now_iso(),
        "decided": None,
        "decision_note": None,
        "source": "audit",
    }
    backend.EVOLUTION.insert(0, item)
    return item


# ── User-friendly audit report (security-auditor + reporter) ───────
# Heuristic "쉬운말" 축약 — proposal 의 kind → 도메인 전문가 친화 문장.
_REASON_SIMPLIFY: dict[str, str] = {
    "split_agent":   "이 에이전트가 너무 오래 걸리므로 역할을 나누면 빨라집니다",
    "retire_agent":  "최근 쓰임이 거의 없어 은퇴 후보입니다",
    "parallelize":   "두 에이전트가 항상 순서대로 도는데 동시에 돌리면 시간 절약됩니다",
    "security_pass": "최근 변경점 중 보안 민감 경로가 있어 권한 재점검 권장합니다",
}


def _proposal_target_label(p: dict) -> str:
    """EVOLUTION item 의 target 을 사람이 읽을 수 있는 라벨로."""
    tgt = p.get("target") or ""
    if isinstance(tgt, list):
        return " + ".join(tgt) if tgt else "(미지정)"
    return str(tgt) if tgt else "(미지정)"


def _simplify_proposal_line(p: dict) -> str:
    """한 proposal 을 bullet 한 줄로 풀어쓴다. heuristic 기본 — LLM
    가용 시 상위 ``build_audit_report`` 에서 통째 다시 써도 된다."""
    kind = p.get("kind") or ""
    hint = _REASON_SIMPLIFY.get(kind, "검토가 필요한 항목입니다")
    label = _proposal_target_label(p)
    return f"{label} — {hint}"


def _bucketize(proposals: list[dict]) -> dict[str, list[dict]]:
    """kind 별로 proposals 를 묶는다. 보고서의 '발견된 패턴' 섹션용."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for p in proposals:
        buckets[p.get("kind") or "unknown"].append(p)
    return dict(buckets)


def _summary_bullets(proposals: list[dict], kind: str) -> list[str]:
    """보고서 맨 위 '핵심 요약' 3줄. proposals 가 비어도 반드시 3줄."""
    total = len(proposals)
    buckets = _bucketize(proposals)
    if total == 0:
        return [
            f"{kind} 감사 완료 — 신규 제안 없음",
            "현재 로스터/구성이 안정적으로 운영되고 있습니다",
            "다음 감사에서 변화점을 다시 확인합니다",
        ]
    top_kinds = Counter({k: len(v) for k, v in buckets.items()}).most_common(2)
    bullets = [f"{kind} 감사 완료 — 총 {total}건의 제안이 올라왔습니다"]
    for k, n in top_kinds:
        bullets.append(
            f"{k} 계열 {n}건 — {_REASON_SIMPLIFY.get(k, '검토 필요')}"
        )
    while len(bullets) < 3:
        bullets.append("자세한 내역은 아래 '발견된 패턴' 섹션을 참고해주세요")
    return bullets[:3]


def _recommend_bullets(proposals: list[dict]) -> list[str]:
    """권고 조치 — kind 별 대표 조치 한 줄씩."""
    if not proposals:
        return ["특별한 조치는 필요 없습니다 — 정기 감사 유지"]
    buckets = _bucketize(proposals)
    out: list[str] = []
    order = ["split_agent", "parallelize", "retire_agent", "security_pass"]
    for k in order:
        if k not in buckets:
            continue
        items = buckets[k]
        targets = ", ".join(_proposal_target_label(p) for p in items[:3])
        if k == "split_agent":
            out.append(f"느린 에이전트 분리 검토: {targets}")
        elif k == "parallelize":
            out.append(f"병렬화 검토: {targets}")
        elif k == "retire_agent":
            out.append(f"은퇴 후보 검토: {targets}")
        elif k == "security_pass":
            out.append(f"보안 재점검: {targets}")
    # 나머지 알 수 없는 kind
    for k, items in buckets.items():
        if k in order:
            continue
        targets = ", ".join(_proposal_target_label(p) for p in items[:3])
        out.append(f"{k} — {targets}")
    return out


def _flag_bullets(proposals: list[dict], kind: str) -> list[str]:
    """주의 플래그 — 보안/은퇴 같은 고위험 신호가 있으면 부각."""
    flags: list[str] = []
    buckets = _bucketize(proposals)
    if kind == "security-big-picture" or "security_pass" in buckets:
        sec_items = buckets.get("security_pass") or []
        if sec_items:
            flags.append(
                f"보안 민감 경로 변경 감지 — 권한 매트릭스 재점검 권장 ({len(sec_items)}건)"
            )
    if "retire_agent" in buckets:
        flags.append(
            f"로스터 정리 필요 — 장기 미사용 에이전트 {len(buckets['retire_agent'])}명"
        )
    if not flags:
        flags.append("특이 위험 신호 없음")
    return flags


def _render_report_body(proposals: list[dict], kind: str) -> str:
    """사용자 친화 markdown 본문을 조립한다. heuristic path."""
    summary = _summary_bullets(proposals, kind)
    recs = _recommend_bullets(proposals)
    flags = _flag_bullets(proposals, kind)

    lines: list[str] = []
    lines.append("## 핵심 요약")
    for b in summary:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("## 발견된 패턴")
    if proposals:
        for p in proposals[:12]:
            lines.append(f"- {_simplify_proposal_line(p)}")
    else:
        lines.append("- 새로 발견된 패턴 없음 — 정상 운영 중")
    lines.append("")
    lines.append("## 권고 조치")
    for r in recs:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("## 주의 플래그")
    for f in flags:
        lines.append(f"- {f}")
    return "\n".join(lines)


# LLM 가용 시 쓰는 압축 system prompt. translator.simplify 는 질문 전용
# 프리셋이라 보고서에는 직접 호출하기보다 자체 prompt 로 돌린다.
_REPORT_LLM_SYSTEM = (
    "당신은 OmniHarness 의 reporter 입니다. security-auditor 가 방금 마친 "
    "감사 결과를 도메인 전문가(개발 배경 약함)가 30초 안에 읽을 수 있게 "
    "한국어 markdown 으로 정리하세요.\n\n"
    "형식 (반드시 이 네 섹션 · 순서 고정):\n"
    "## 핵심 요약\n- 3줄\n\n"
    "## 발견된 패턴\n- bullet\n\n"
    "## 권고 조치\n- bullet\n\n"
    "## 주의 플래그\n- bullet\n\n"
    "규칙: 영어 기술 용어는 풀어쓰고, 숫자는 맥락과 함께 제시, "
    "과장 금지. 제안이 0건이면 '변경점 없음 — 통과' 를 명확히 알려주세요."
)


def _render_report_body_llm(proposals: list[dict], kind: str) -> str | None:
    """LLM 경로. translator._llm_call 이 anthropic > bedrock > openai >
    gemini 순으로 시도한다. 전부 실패하면 None → heuristic 으로 fallback."""
    # proposal 을 LLM 에 넘길 때는 과도한 metric payload 는 제거해 토큰 절약.
    slim = [
        {
            "kind": p.get("kind"),
            "target": _proposal_target_label(p),
            "reason": p.get("reason") or p.get("rationale") or "",
        }
        for p in proposals[:20]
    ]
    user_msg = (
        f"[감사 유형] {kind}\n"
        f"[제안 건수] {len(proposals)}\n"
        f"[제안 목록 JSON]\n{slim}\n\n"
        "위 제안을 바탕으로 네 섹션 보고서를 작성하세요."
    )
    try:
        from translator import _llm_call  # type: ignore
    except Exception:
        return None
    try:
        return _llm_call(_REPORT_LLM_SYSTEM, user_msg)
    except Exception:
        return None


def build_audit_report(proposals: list[dict], kind: str) -> dict:
    """사용자 친화 감사 보고서를 만들어 dict 로 반환. REPORTS insert 대상.

    - ``kind`` 는 "audit" 또는 "security-big-picture".
    - proposals 가 비어 있어도 "통과" 보고서 한 건을 반드시 생성.
    - LLM 경로 우선, 실패 시 heuristic fallback.
    """
    import app as backend
    body = _render_report_body_llm(proposals, kind) or _render_report_body(
        proposals, kind
    )
    kind_ko = "정기 감사" if kind == "audit" else "big-picture 보안 점검"
    title_prefix = "[정기 감사]" if kind == "audit" else "[big-sec]"
    title_tail = (
        f"제안 {len(proposals)}건" if proposals else "변경점 없음 — 통과"
    )
    item = {
        "id": str(uuid.uuid4())[:8],
        "title": f"{title_prefix} {kind_ko} — {title_tail}",
        "agent": "reporter",
        "author": "reporter",
        "body": body,
        "content_md": body,           # list_reports 는 요약만 반환하지만
                                      # GET /api/reports/{rid} 호환 위해.
        "created": backend.now_iso(),
        "source": kind,
        "severity": (
            "warning" if any(
                p.get("kind") == "security_pass" for p in proposals
            ) else "info"
        ),
        "tags": ["audit", kind],
        "summary": (
            _summary_bullets(proposals, kind)[0] if proposals
            else f"{kind_ko} 완료 — 신규 제안 없음"
        ),
        "sections": [
            {"heading": "핵심 요약", "body": "",
             "bullets": _summary_bullets(proposals, kind), "metric": None},
            {"heading": "발견된 패턴", "body": "",
             "bullets": (
                 [_simplify_proposal_line(p) for p in proposals[:12]]
                 if proposals else ["새로 발견된 패턴 없음 — 정상 운영 중"]
             ), "metric": None},
            {"heading": "권고 조치", "body": "",
             "bullets": _recommend_bullets(proposals), "metric": None},
            {"heading": "주의 플래그", "body": "",
             "bullets": _flag_bullets(proposals, kind), "metric": None},
        ],
        "metrics": {"proposal_count": len(proposals)},
        "proposal_ids": [p.get("id") for p in proposals if p.get("id")],
    }
    return item


# Dedup window for audit REPORTS. If an identical report (same title +
# source + same set of proposal_ids) already sits at the top of REPORTS
# within the last hour, we skip republishing. Distinct proposal sets
# still produce a fresh report — the guard only kills literal repeats.
_REPORT_DEDUP_WINDOW_S = 60 * 60  # 1 hour


def _find_recent_duplicate_report(title: str, source: str, proposal_ids: list) -> dict | None:
    """Return a REPORTS item that matches title + source + proposal_ids
    and was created within ``_REPORT_DEDUP_WINDOW_S`` seconds, else None."""
    import app as backend
    now = time.time()
    pid_set = set(proposal_ids or [])
    for r in backend.REPORTS:
        if r.get("source") != source:
            continue
        if r.get("title") != title:
            continue
        created = _parse_ts(r.get("created") or "")
        if created is None:
            continue
        if (now - created) > _REPORT_DEDUP_WINDOW_S:
            # REPORTS is newest-first; older matches can't narrow any
            # further, bail out.
            return None
        if set(r.get("proposal_ids") or []) == pid_set:
            return r
    return None


def _publish_audit_report(proposals: list[dict], kind: str) -> dict:
    """보고서를 만들어 REPORTS 앞에 insert 하고, reporter 블링크 + activity
    2건을 남긴다. 반환값은 insert 된 REPORTS item.

    Dedup guard: if the same audit run (identical title + source + the
    exact same set of proposal ids) already exists within the last hour,
    skip the insert and return the existing report. Prevents the viewer
    from showing two "[정기 감사] 제안 1건" cards for a single finding.
    """
    import app as backend

    # Build the report up-front so we can compare against existing
    # entries without duplicating title-construction logic.
    report = build_audit_report(proposals, kind)
    dup = _find_recent_duplicate_report(
        title=report.get("title") or "",
        source=kind,
        proposal_ids=report.get("proposal_ids") or [],
    )
    if dup is not None:
        backend.log_event(
            "reporter", "report",
            f"동일 감사 보고서 1시간 내 중복 — 재발행 스킵 ({dup.get('id')})",
        )
        return dup

    # reporter working 블링크 진입
    try:
        prev = backend.STATES.get("reporter", "idle")
        if prev != "working":
            backend.STATES["reporter"] = "working"
            backend.log_event("reporter", "state", f"{prev} → working")
            try:
                backend._accrue_for_state_working("reporter")
            except Exception:
                pass
    except Exception:
        pass
    backend.log_event(
        "security-auditor", "audit",
        f"감사 보고서 취합 중 ({kind}, 제안 {len(proposals)}건)",
    )

    try:
        backend.REPORTS.insert(0, report)
    except Exception:
        pass

    backend.log_event(
        "reporter", "report",
        f"사용자 친화 요약 완료 — {report.get('title', '감사 보고서')}",
    )

    # reporter idle 로 복귀
    try:
        prev = backend.STATES.get("reporter", "idle")
        if prev != "idle":
            backend.STATES["reporter"] = "idle"
            backend.log_event("reporter", "state", f"{prev} → idle")
    except Exception:
        pass
    return report


# ── Entrypoints ─────────────────────────────────────────────────────
def run_audit_pass() -> list[dict]:
    """Synchronous audit. Returns the list of newly-created proposals."""
    global LAST_AUDIT_AT, AUDIT_COUNT
    import app as backend

    # Viewer lights: hr + security-auditor flip to working for the pass.
    for a in ("hr", "security-auditor"):
        try:
            prev = backend.STATES.get(a, "idle")
            if prev != "working":
                backend.STATES[a] = "working"
                backend.log_event(a, "state", f"{prev} → working")
                try:
                    backend._accrue_for_state_working(a)
                except Exception:
                    pass
        except Exception:
            pass
    backend.log_event("hr", "audit", "감사 시작")

    activity = _iter_activity()
    cost_by_agent = dict(getattr(backend, "COST_BY_AGENT", {}) or {})
    roster = _roster_names()
    raw = _build_proposals(activity, cost_by_agent, roster)

    created: list[dict] = []
    for p in raw:
        item = add_audit_proposal(
            kind=p["kind"],
            reason=p["reason"],
            target=p.get("target") or p.get("targets") or "",
            metric=p.get("metric") or {},
        )
        created.append(item)

    AUDIT_COUNT += 1
    LAST_AUDIT_AT = backend.now_iso()

    backend.log_event(
        "hr", "audit",
        f"{AUDIT_COUNT}번째 감사 완료 — 제안 {len(created)}건",
    )

    # Publish user-friendly digest into REPORTS (reporter + security-auditor
    # joint output). Always emits exactly one report per pass — even when
    # ``created`` is empty, so operators see "audit ran but found nothing".
    try:
        _publish_audit_report(created, kind="audit")
    except Exception:
        # Report publication must never break the audit pass itself.
        pass

    # Flip helpers back to idle so the viewer returns to rest.
    for a in ("hr", "security-auditor"):
        try:
            prev = backend.STATES.get(a, "idle")
            if prev != "idle":
                backend.STATES[a] = "idle"
                backend.log_event(a, "state", f"{prev} → idle")
        except Exception:
            pass
    try:
        backend._save_state()
    except Exception:
        pass
    return created


async def run_audit_pass_async() -> list[dict]:
    """Async wrapper — yields once so we don't monopolise the loop when
    called via ``asyncio.create_task``. The work itself is synchronous
    and fast (O(|ACTIVITY|)), so we don't offload to a thread."""
    await asyncio.sleep(0)
    return run_audit_pass()


# ── Big-picture security pass ──────────────────────────────────────
def _recent_touched_files(activity: list[dict], max_runs: int = 5) -> set[str]:
    """Return the set of files touched by Edit/Write tool events across
    the last ``max_runs`` coordinator runs (run boundaries inferred the
    same way as ``_coordinator_runs``).

    Tool events are logged with ``kind='tool'`` and a detail string that
    typically contains a path; we scan for whitespace-delimited tokens
    that look like paths (have a '/' or '\\' or a file extension) and
    collect them. Intentionally lossy — we just need a rough touched-
    files set to steer the proposal text.
    """
    # Locate the last ``max_runs`` '요구사항 수신' markers so we only
    # scan within that recent window.
    starts: list[int] = []
    for i, ev in enumerate(activity):
        if (
            ev.get("agent") == "orchestrator"
            and ev.get("kind") == "coord"
            and (ev.get("detail") or "").startswith("요구사항 수신")
        ):
            starts.append(i)
    window_start = starts[-max_runs] if len(starts) >= max_runs else (starts[0] if starts else 0)

    touched: set[str] = set()
    for ev in activity[window_start:]:
        if ev.get("kind") != "tool":
            continue
        detail = ev.get("detail") or ""
        # Split on whitespace + common punctuation. Paths typically
        # contain '/' or '\\' or a dot-extension — filter on that.
        for tok in detail.replace(",", " ").replace("(", " ").replace(")", " ").split():
            if ("/" in tok or "\\" in tok) and len(tok) < 200:
                touched.add(tok.strip(".,;:\"'`"))
            elif "." in tok and len(tok) < 80 and not tok.startswith("."):
                # bare filenames like "config.py"
                touched.add(tok.strip(".,;:\"'`"))
    return touched


def add_big_security_proposal(reason: str, target: str, metric: dict) -> dict:
    """Insert a big-picture security proposal into EVOLUTION with a
    distinct ``source='security-big-picture'`` tag so the viewer can
    separate per-change and big-picture security findings.

    Shares ``add_audit_proposal``'s dedup policy: proposed → refresh in
    place, decided-within-24h → skip, otherwise insert fresh.
    """
    import app as backend
    target_key = _normalize_target(target)
    existing = _find_evolution_dup(
        "security_pass", target_key, source="security-big-picture"
    )
    if existing is not None:
        status = existing.get("status")
        if status == "proposed":
            existing["reason"] = reason
            existing["rationale"] = reason
            payload = dict(existing.get("payload") or {})
            payload["metric"] = metric
            payload["target"] = target
            existing["payload"] = payload
            existing["created"] = backend.now_iso()
            return existing
        decided_at = _parse_ts(existing.get("decided") or existing.get("created") or "")
        if decided_at is not None and (time.time() - decided_at) < _EVO_DEDUP_DECIDED_WINDOW_S:
            return existing

    eid = str(uuid.uuid4())[:8]
    item = {
        "id": eid,
        "agent": "security-auditor",
        "kind": "security_pass",
        "title": f"[big-sec] {target}",
        "rationale": reason,
        "reason": reason,
        "target": target,
        "payload": {"metric": metric, "target": target},
        "status": "proposed",
        "created": backend.now_iso(),
        "decided": None,
        "decision_note": None,
        "source": "security-big-picture",
    }
    backend.EVOLUTION.insert(0, item)
    return item


def _big_security_proposals(touched: set[str]) -> list[dict]:
    """Build 1–3 big-picture security findings from the touched-files
    set. Purely heuristic — we pattern-match on well-known sensitive
    subtrees. Returns a list of ``{target, reason, metric}`` dicts.
    """
    proposals: list[dict] = []

    sensitive_hits = sorted(
        {p for p in touched if any(h in p for h in _SENSITIVE_PATH_HINTS)}
    )
    config_hits = sorted(
        {p for p in touched if any(h in p.lower() for h in _CONFIG_FILE_HINTS)}
    )

    if sensitive_hits:
        proposals.append({
            "target": "전체 권한 매트릭스 재점검",
            "reason": (
                f"최근 변경점이 보안 민감 경로(routers/ · core/)에 걸침 — "
                f"{len(sensitive_hits)}개 경로 변경. 역할 × 엔드포인트 권한 "
                f"매트릭스를 엔드-투-엔드로 재점검 권장"
            ),
            "metric": {
                "touched_sensitive": sensitive_hits[:10],
                "sensitive_count": len(sensitive_hits),
            },
        })
    if config_hits:
        proposals.append({
            "target": "config 변경 이력 + 접근권한 점검",
            "reason": (
                f"민감 config(DVC · env · settings) 변경 감지 — "
                f"{len(config_hits)}건. 변경 이력과 접근권한(누가 수정 가능, "
                f"secret rotation 필요 여부) 점검 권장"
            ),
            "metric": {
                "touched_config": config_hits[:10],
                "config_count": len(config_hits),
            },
        })
    if not proposals:
        proposals.append({
            "target": "변경점 없음 — 통과",
            "reason": (
                "최근 코디네이터 런에서 민감 경로/구성 변경이 감지되지 않음. "
                "현재 권한 매트릭스 유지로 충분"
            ),
            "metric": {"touched_total": len(touched)},
        })
    return proposals[:3]


def run_big_security_pass() -> list[dict]:
    """Big-picture security pass — runs every BIG_SECURITY_EVERY
    coordinator completions (scheduled from app.on_coordinator_complete)
    or on demand via POST /api/audit/security/run.

    Emits 1–3 EVOLUTION proposals tagged ``source='security-big-picture'``.
    """
    global LAST_BIG_SECURITY_AT, BIG_SECURITY_COUNT
    import app as backend

    # Viewer lights: security-auditor flips working for the pass.
    try:
        prev = backend.STATES.get("security-auditor", "idle")
        if prev != "working":
            backend.STATES["security-auditor"] = "working"
            backend.log_event("security-auditor", "state", f"{prev} → working")
            try:
                backend._accrue_for_state_working("security-auditor")
            except Exception:
                pass
    except Exception:
        pass
    backend.log_event(
        "security-auditor", "audit",
        "big-picture 보안 점검 시작 — 전체 파일 트리 기준 관점",
    )

    activity = _iter_activity()
    touched = _recent_touched_files(activity, max_runs=5)
    raw = _big_security_proposals(touched)

    created: list[dict] = []
    for p in raw:
        item = add_big_security_proposal(
            reason=p["reason"],
            target=p["target"],
            metric=p.get("metric") or {},
        )
        created.append(item)

    BIG_SECURITY_COUNT += 1
    LAST_BIG_SECURITY_AT = backend.now_iso()

    backend.log_event(
        "security-auditor", "audit",
        f"{BIG_SECURITY_COUNT}번째 big-picture 보안 점검 완료 — 제안 {len(created)}건",
    )

    # Publish user-friendly digest into REPORTS. Tagged with the
    # security-big-picture source so the viewer can distinguish it from
    # the periodic audit reports.
    try:
        _publish_audit_report(created, kind="security-big-picture")
    except Exception:
        pass

    # Flip back to idle.
    try:
        prev = backend.STATES.get("security-auditor", "idle")
        if prev != "idle":
            backend.STATES["security-auditor"] = "idle"
            backend.log_event("security-auditor", "state", f"{prev} → idle")
    except Exception:
        pass
    try:
        backend._save_state()
    except Exception:
        pass
    return created


async def run_big_security_pass_async() -> list[dict]:
    """Async wrapper for ``run_big_security_pass`` — same rationale as
    ``run_audit_pass_async``: yield once then do the (fast) sync work."""
    await asyncio.sleep(0)
    return run_big_security_pass()


def status() -> dict:
    """Used by GET /api/audit/status."""
    import app as backend
    every = int(os.environ.get("OMNI_AUDIT_EVERY", "15"))
    big_every = int(os.environ.get("SECURITY_AUDIT_EVERY", "10"))
    completed = int(getattr(backend, "COORDINATOR_COMPLETED", 0))
    # next audit fires when (completed + 1) % every == 0; surface the
    # absolute coordinator-count milestone rather than a wall-clock.
    remainder = completed % every
    next_at = completed + (every - remainder) if remainder != 0 else completed + every
    big_remainder = completed % big_every
    next_big_at = (
        completed + (big_every - big_remainder) if big_remainder != 0
        else completed + big_every
    )
    return {
        "completed_coordinators": completed,
        "audit_count": AUDIT_COUNT,
        "last_audit_at": LAST_AUDIT_AT,
        "next_audit_at_nth": next_at,
        "audit_every": every,
        "big_security_every": big_every,
        "big_security_count": BIG_SECURITY_COUNT,
        "last_big_security_at": LAST_BIG_SECURITY_AT,
        "next_big_security_at_nth": next_big_at,
        "thresholds": {
            "slow_working_s": SLOW_WORKING_S,
            "idle_runs_n": IDLE_RUNS_N,
            "parallel_min_cooccurrence": PARALLEL_MIN_COOCCURRENCE,
        },
    }
