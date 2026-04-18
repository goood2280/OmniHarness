"""Claude Code hook bridge → OmniHarness Viewer.

Reads a hook event from stdin (JSON), extracts the relevant info,
and POSTs it to the OmniHarness backend so the pixel-office viewer
lights up the correct agent and appends an activity log entry.

Usage (from .claude/settings.json on the consumer project):

  {
    "hooks": {
      "PreToolUse": [
        { "matcher": "Agent", "hooks": [
          { "type": "command",
            "command": "python /path/to/OmniHarness/scripts/hook_to_omniharness.py pre" }
        ]}
      ],
      "PostToolUse": [
        { "matcher": "Agent", "hooks": [
          { "type": "command",
            "command": "python /path/to/OmniHarness/scripts/hook_to_omniharness.py post" }
        ]},
        { "matcher": "Edit|Write|Bash", "hooks": [
          { "type": "command",
            "command": "python /path/to/OmniHarness/scripts/hook_to_omniharness.py tool" }
        ]}
      ],
      "UserPromptSubmit": [
        { "hooks": [
          { "type": "command",
            "command": "python /path/to/OmniHarness/scripts/hook_to_omniharness.py prompt" }
        ]}
      ]
    }
  }

The script never raises; on any failure it silently exits 0 so Claude Code
is never blocked by viewer downtime.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

OMNI = "http://localhost:8081"

# Our canonical agent names (must match templates/agents/*.md)
KNOWN_AGENTS = {
    "orchestrator", "dev-lead", "mgmt-lead", "eval-lead",
    "be-dashboard", "be-filebrowser", "be-tracker",
    "fe-dashboard", "fe-filebrowser", "fe-tracker",
    "reporter", "hr",
    "ux-reviewer", "dev-verifier", "user-tester", "admin-tester",
    "feature-auditor", "industry-researcher",
}


def post(path: str, body: dict) -> None:
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            OMNI + path, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=1.5).read()
    except (urllib.error.URLError, TimeoutError, Exception):
        # viewer offline — don't fail the hook
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
    """Pull the subagent_type from a Task/Agent tool event. Fall back to None."""
    tin = ev.get("tool_input") or {}
    # Claude Code's Agent tool uses `subagent_type`
    for k in ("subagent_type", "agent", "agentType"):
        v = tin.get(k)
        if isinstance(v, str) and v in KNOWN_AGENTS:
            return v
    # Sometimes it's nested under `tool_use.input`
    tu = ev.get("tool_use") or {}
    ti = tu.get("input") or {}
    for k in ("subagent_type", "agent"):
        v = ti.get(k)
        if isinstance(v, str) and v in KNOWN_AGENTS:
            return v
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
        # A Read/Edit/Write/Bash ran inside the main (or a subagent).
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
