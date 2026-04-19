"""Claude Code hook bridge → OmniHarness Viewer.

Reads a hook event from stdin (JSON), extracts the relevant info, and
POSTs it to the OmniHarness backend so the office scene / general tree
lights up the correct agent and appends an activity log entry.

Configure the target with `OMNIHARNESS_URL` env var (defaults to
http://localhost:8082). On any failure the script exits 0 so Claude
Code is never blocked by viewer downtime.

Usage — add to `.claude/settings.json`:

  {
    "hooks": {
      "PreToolUse":  [ { "matcher": "Agent|Task",
                         "hooks": [{ "type": "command",
                                     "command": "python /path/OmniHarness/scripts/hook_to_omniharness.py pre" }] } ],
      "PostToolUse": [
        { "matcher": "Agent|Task",
          "hooks": [{ "type": "command",
                      "command": "python /path/OmniHarness/scripts/hook_to_omniharness.py post" }] },
        { "matcher": "Edit|Write|Bash|Read|Grep|Glob",
          "hooks": [{ "type": "command",
                      "command": "python /path/OmniHarness/scripts/hook_to_omniharness.py tool" }] }
      ],
      "UserPromptSubmit": [ { "hooks": [{ "type": "command",
                                          "command": "python /path/OmniHarness/scripts/hook_to_omniharness.py prompt" }] } ]
    }
  }
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

OMNI = os.environ.get("OMNIHARNESS_URL", "http://localhost:8082").rstrip("/")

# Canonical roster — mirrors BASE_ROLES + DEV_CATALOG + DOMAIN_CATALOG in
# backend/app.py. Keep these in sync when templates change.
KNOWN_AGENTS = {
    # Base (always)
    "orchestrator", "dev-lead", "mgmt-lead", "eval-lead",
    "reporter", "hr",
    "ux-reviewer", "dev-verifier", "user-role-tester", "admin-role-tester",
    "security-auditor", "domain-researcher",
    # Dev catalog
    "dev-dashboard", "dev-spc", "dev-wafer-map", "dev-ml", "dev-ettime",
    "dev-tablemap", "dev-tracker", "dev-filebrowser", "dev-admin", "dev-messages",
    # Domain catalog
    "process-tagger", "causal-analyst", "dvc-curator", "adapter-engineer",
}


def post(path: str, body: dict) -> None:
    try:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            OMNI + path, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=1.5).read()
    except (urllib.error.URLError, TimeoutError, Exception):
        # viewer offline — never block the hook
        pass


def read_stdin() -> dict:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        return json.loads(raw)
    except Exception:
        return {}


def subagent_from(ev: dict) -> str | None:
    """Pull a known subagent name out of a Task/Agent event's input."""
    candidates = []
    tin = ev.get("tool_input") or {}
    for k in ("subagent_type", "agent", "agentType", "name"):
        v = tin.get(k)
        if isinstance(v, str):
            candidates.append(v)
    tu = ev.get("tool_use") or {}
    ti = tu.get("input") or {}
    for k in ("subagent_type", "agent"):
        v = ti.get(k)
        if isinstance(v, str):
            candidates.append(v)
    for c in candidates:
        if c in KNOWN_AGENTS:
            return c
    return None


def main(kind: str) -> int:
    ev = read_stdin()

    if kind == "pre":
        name = subagent_from(ev)
        if name:
            post(f"/api/agents/{name}/state", {"state": "working"})
            desc = ((ev.get("tool_input") or {}).get("description")
                    or (ev.get("tool_input") or {}).get("prompt", "")[:60])
            post("/api/activity", {"agent": name, "kind": "invoke",
                                   "detail": f"호출됨: {desc}"[:200]})

    elif kind == "post":
        name = subagent_from(ev)
        if name:
            post(f"/api/agents/{name}/state", {"state": "idle"})
            post("/api/activity", {"agent": name, "kind": "complete",
                                   "detail": "작업 완료 · idle 복귀"})

    elif kind == "tool":
        tname = ev.get("tool_name") or (ev.get("tool_use") or {}).get("name") or "tool"
        tin = ev.get("tool_input") or {}
        fp = tin.get("file_path") or tin.get("command") or tin.get("pattern") or ""
        # Attribute to orchestrator unless we can tell otherwise
        post("/api/activity", {
            "agent": "orchestrator",
            "kind": "tool",
            "detail": f"{tname} · {str(fp)[:80]}",
        })

    elif kind == "prompt":
        text = ev.get("prompt") or ev.get("message") or ""
        post("/api/activity", {
            "agent": "orchestrator", "kind": "user-prompt",
            "detail": f"사용자 요청: {str(text)[:120]}",
        })

    return 0


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "tool"
    sys.exit(main(arg))
