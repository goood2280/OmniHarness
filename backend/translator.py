"""mgmt-lead 번역 파이프라인 — raw 질문을 도메인 전문가 친화적으로 simplify.

두 가지 경로:

1. **LLM 모드** (``_llm_call`` 이 plain-text 를 돌려주면 그걸 사용):
   우선순위는 ``ANTHROPIC_API_KEY`` > ``CLAUDE_CODE_USE_BEDROCK`` >
   ``OPENAI_API_KEY`` > ``GEMINI_API_KEY``. 없는 provider 는 다음으로
   fallthrough 하고, 전부 실패하면 heuristic.

2. **Heuristic 모드** (provider 없음 · SDK 없음 · LLM 호출 실패):
   - 첫 줄: raw 의 첫 문장을 한 줄 요약.
   - 둘째 줄: context.agent 의 역할 문맥 ("~이 ~를 결정해야 함").
   - 선택지 패턴 감지 → bullet 재포맷.
   - 각 bullet 에 "→ 이 경우 ..." 한 줄 힌트 (보수적).

app.py 에서 ``simplify(raw, {"agent": q.agent})`` 로 호출한다. 항상
str 을 반환 — 예외는 호출부가 잡아서 raw 로 fallback 하게 설계.
"""
from __future__ import annotations

import logging
import os
import re


_log = logging.getLogger("omniharness.translator")


# ── 에이전트 역할 문맥 (slimmed 2026-04-19) ─────────────────────────
# 극장 레이어 제거 — dev-* 10개 / 도메인 4개 / mgmt-lead / reporter /
# hr / eval-lead 모두 orchestrator + dev-lead + reviewer 6 에 흡수.
# 이 dict 는 orchestrator 가 유저에게 질문을 **평어체로 직접** 쓸 때
# "누구 입장에서의 질문인지" 한 줄 힌트만 제공.
_AGENT_ROLE_KO: dict[str, str] = {
    "orchestrator":      "오케스트레이터가 흐름/전체 구조를",
    "dev-lead":          "개발자가 구현 방식을",
    "ux-reviewer":       "UX 리뷰어가 사용자 흐름을",
    "dev-verifier":      "개발 검증자가 빌드/런타임 검증 범위를",
    "user-role-tester":  "유저 롤 테스터가 시나리오를",
    "admin-role-tester": "관리자 롤 테스터가 시나리오를",
    "security-auditor":  "보안 감사자가 위협 범위를",
    "domain-researcher": "도메인 리서처가 조사 범위를",
}


def _role_context(agent: str | None) -> str:
    """사용자 친화 역할 문맥 한 줄. 모르는 agent 는 일반 문구."""
    if not agent:
        return "담당 에이전트가 결정을 앞두고"
    return _AGENT_ROLE_KO.get(agent, f"{agent} 가 결정을")


# ── 선택지 감지 ────────────────────────────────────────────────────
_OPT_PATTERNS = [
    # "(A) ... (B) ... (C) ..."
    re.compile(r"\(([A-Za-z])\)\s*([^()]+?)(?=\s*\([A-Za-z]\)|$)", re.DOTALL),
    # "A: ... B: ..."
    re.compile(r"(?:^|\s)([A-Z])[:\-]\s*([^A-Z\n][^\n]+)"),
]


def _detect_options(raw: str) -> list[tuple[str, str]]:
    """raw 에서 (label, text) 튜플 리스트를 뽑는다. 없으면 빈 리스트.

    첫 번째 패턴이 히트하면 그걸 채택 (중복 매칭 방지). "A or B",
    "X 또는 Y" 같은 순수 자연어는 여기선 안 잡는다 — 너무 공격적으로
    split 하면 오작동 — LLM 모드에 맡긴다.
    """
    # (A)/(B) 스타일
    m = _OPT_PATTERNS[0].findall(raw)
    if m and len(m) >= 2:
        return [(lab.upper(), txt.strip(" ,.。")) for lab, txt in m]
    # "- X\n- Y" dash bullet 스타일
    dash = re.findall(r"(?m)^\s*[-*]\s+(.+)$", raw)
    if len(dash) >= 2:
        labels = "ABCDEFG"
        return [(labels[i], t.strip()) for i, t in enumerate(dash)]
    # "A or B?" 간단 케이스 — 단어 2~4개 기준
    mo = re.search(r"\b([A-Za-z_][\w\-./]{1,40})\s+(?:vs|or|또는)\s+([A-Za-z_][\w\-./]{1,40})\b", raw)
    if mo:
        return [("A", mo.group(1).strip()), ("B", mo.group(2).strip())]
    return []


def _first_sentence(raw: str) -> str:
    raw = raw.strip()
    # ? . ! 。 중 첫 문장
    m = re.search(r"^(.+?[?!.。])\s", raw + " ")
    s = m.group(1) if m else raw
    return s.strip()


def _bullet_hint(label: str, text: str) -> str:
    """bullet 한 줄 옆의 '→ 이 경우 ...' 짧은 해설. heuristic 이라
    과감한 해석은 피함 — 단순 힌트만."""
    t = text.lower()
    # 우선순위 / default 류
    if any(k in t for k in ("우선", "priority", "먼저", "first", "default")):
        return "→ 이쪽이 기본값이 됨"
    if any(k in t for k in ("env", "환경변수", "환경 변수")):
        return "→ 배포 환경에서 값 주입"
    if any(k in t for k in ("db", "admin_settings", "settings", "설정")):
        return "→ 런타임 중 UI 로 변경 가능"
    if any(k in t for k in ("새로", "신규", "new")):
        return "→ 새로 만들어야 함"
    if any(k in t for k in ("기존", "existing")):
        return "→ 이미 있는 것을 활용"
    return ""


# ── Heuristic 본체 ─────────────────────────────────────────────────
def _simplify_heuristic(raw: str, context: dict | None) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    agent = (context or {}).get("agent")
    lines: list[str] = []
    # (1) 첫 줄: 질문 한 줄 요약
    q_line = _first_sentence(raw)
    if not q_line.endswith(("?", "？")):
        # 의문형이 아니면 질문 뉘앙스 부여
        q_line = q_line.rstrip(".。 ") + " — 어떻게 갈까요?"
    lines.append(f"질문: {q_line}")

    # (2) 역할 문맥
    lines.append(f"맥락: {_role_context(agent)} 결정해야 합니다.")

    # (3) 선택지 bullet
    opts = _detect_options(raw)
    if opts:
        lines.append("선택지:")
        for lab, txt in opts[:5]:
            hint = _bullet_hint(lab, txt)
            if hint:
                lines.append(f"  ({lab}) {txt}  {hint}")
            else:
                lines.append(f"  ({lab}) {txt}")
    else:
        lines.append("선택지: (자유 서술 — 편하게 한 줄로 답해주세요)")

    return "\n".join(lines)


# ── LLM 본체 ───────────────────────────────────────────────────────
_LLM_SYSTEM = (
    "당신은 OmniHarness 의 mgmt-lead 입니다. 개발 에이전트가 사용자에게 묻는 "
    "기술적 질문을, 도메인 전문가(반도체/제조 현장 전문가지만 개발 배경은 약한 "
    "사람)가 바로 이해하고 답할 수 있도록 한국어로 풀어써주세요.\n\n"
    "형식:\n"
    "- 3~6 줄\n"
    "- 첫 줄은 '질문:' 으로 시작해 한 줄 요약\n"
    "- 둘째 줄은 '맥락:' 으로 시작해 '왜 이 결정이 필요한지' 짧게\n"
    "- 선택지가 있으면 '선택지:' 아래 (A)/(B)/(C) bullet 로 정리하고 각 옵션 뒤에 "
    "  '→ 이 경우 ...' 짧은 해설\n"
    "- 선택지가 없으면 '선택지: (자유 서술)' 한 줄\n"
    "- 영어 기술 용어는 풀어쓰거나 괄호로 한글 설명 첨부\n"
    "- 절대 원문을 그대로 복사하지 말 것"
)


# ── Multi-provider LLM dispatch ────────────────────────────────────
#
# Priority (first that is usable wins):
#   1. ANTHROPIC_API_KEY          — anthropic SDK, claude-haiku-4-5
#   2. CLAUDE_CODE_USE_BEDROCK=1  — boto3 → AWS Bedrock, same Claude
#   3. OPENAI_API_KEY             — openai SDK, gpt-4o-mini (override via OPENAI_MODEL)
#   4. GEMINI_API_KEY             — google-genai SDK, gemini-2.5-flash (override via GEMINI_MODEL)
#
# 각 provider 는 optional import — 패키지 또는 키가 없으면 다음
# provider 로 fallthrough. 전부 실패하면 None → heuristic 폴백.
def _llm_anthropic(system: str, user: str) -> str | None:
    try:
        import anthropic  # type: ignore
    except Exception:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        _log.info("translator._llm_call: anthropic 경로 진입")
        client = anthropic.Anthropic(api_key=api_key)
        model = os.environ.get(
            "ANTHROPIC_SMALL_FAST_MODEL",
            "claude-haiku-4-5-20251001",
        )
        resp = client.messages.create(
            model=model,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts: list[str] = []
        for blk in getattr(resp, "content", []) or []:
            txt = getattr(blk, "text", None)
            if isinstance(txt, str):
                parts.append(txt)
        out = "\n".join(parts).strip()
        return out or None
    except Exception as e:
        _log.warning("translator._llm_call: anthropic 실패 (%s)", e)
        return None


def _llm_bedrock(system: str, user: str) -> str | None:
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") != "1" \
            and not os.environ.get("AWS_ACCESS_KEY_ID"):
        return None
    try:
        import boto3  # type: ignore
    except Exception:
        return None
    try:
        _log.info("translator._llm_call: bedrock 경로 진입")
        region = os.environ.get("AWS_REGION", "us-east-1")
        model = os.environ.get(
            "ANTHROPIC_SMALL_FAST_MODEL",
            "anthropic.claude-haiku-4-5-20251001-v1:0",
        )
        client = boto3.client("bedrock-runtime", region_name=region)
        resp = client.converse(
            modelId=model,
            messages=[{"role": "user", "content": [{"text": user}]}],
            system=[{"text": system}],
            inferenceConfig={"maxTokens": 512},
        )
        out = resp.get("output", {}).get("message", {})
        parts = [c.get("text", "") for c in out.get("content", []) if c.get("text")]
        text = "\n".join(parts).strip()
        return text or None
    except Exception as e:
        _log.warning("translator._llm_call: bedrock 실패 (%s)", e)
        return None


def _llm_openai(system: str, user: str) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None
    try:
        _log.info("translator._llm_call: openai 경로 진입")
        client = OpenAI(api_key=api_key)
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        choice = (resp.choices or [None])[0]
        text = (getattr(getattr(choice, "message", None), "content", "") or "").strip()
        return text or None
    except Exception as e:
        _log.warning("translator._llm_call: openai 실패 (%s)", e)
        return None


def _llm_gemini(system: str, user: str) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore
    except Exception:
        return None
    try:
        _log.info("translator._llm_call: gemini 경로 진입")
        client = genai.Client(api_key=api_key)
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        resp = client.models.generate_content(
            model=model,
            contents=user,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=512,
            ),
        )
        text = (getattr(resp, "text", "") or "").strip()
        return text or None
    except Exception as e:
        _log.warning("translator._llm_call: gemini 실패 (%s)", e)
        return None


def _llm_call(system: str, user: str) -> str | None:
    """Run ``(system, user)`` through the first usable LLM provider.

    Returns the plain-text response, or ``None`` when no provider is
    available / all providers failed. Provider priority is documented
    at the top of this section.
    """
    for fn in (_llm_anthropic, _llm_bedrock, _llm_openai, _llm_gemini):
        out = fn(system, user)
        if out:
            return out
    return None


def _simplify_llm(raw: str, context: dict | None) -> str | None:
    """LLM 경로. 실패 시 None 을 반환해 호출부가 heuristic 으로 떨어지게
    한다. 예외는 ``_llm_call`` 이 흡수."""
    agent = (context or {}).get("agent") or "unknown"
    role_hint = _role_context(agent)
    user_msg = (
        f"[질문을 던진 에이전트] {agent}\n"
        f"[역할 문맥] {role_hint}\n\n"
        f"[원문 질문]\n{raw.strip()}\n\n"
        "위 질문을 도메인 전문가가 바로 답할 수 있게 한국어로 풀어쓰세요."
    )
    return _llm_call(_LLM_SYSTEM, user_msg)


# ── Public API ─────────────────────────────────────────────────────
def simplify(raw: str, context: dict | None = None) -> str:
    """raw 질문을 도메인 전문가 친화적으로 풀어쓴 한국어 텍스트를 반환.

    - LLM 모드가 가능하면 먼저 시도.
    - 실패/비활성이면 heuristic.
    - 둘 다 빈 문자열이면 raw 원문을 반환 (호출부가 pending_user 로
      올릴 때 화면에 적어도 원문이 보이게 보장).
    """
    if not raw or not raw.strip():
        return raw or ""
    llm_out = _simplify_llm(raw, context)
    if llm_out:
        return llm_out
    heur = _simplify_heuristic(raw, context)
    return heur or raw
