#!/usr/bin/env bash
# Fires before the Write tool AND before Bash. Deliberately incomplete on purpose —
# see docs/LAB4-HOOKS.md §4.1 for what this is meant to demonstrate.
#
# Stage 1: blocks the Write tool outright.
# Stage 2 (this version): also blocks Bash commands that use `cat` to write a file.

# Prefer python3 (Mac/Linux default); fall back to python (e.g. some Windows installs).
command -v python3 >/dev/null 2>&1 && PY=python3 || PY=python

# Claude Code sends one JSON object on stdin describing the tool call.
INPUT=$(cat)
TOOL=$("$PY" -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_name") or "")
' <<<"$INPUT")

# Same deny shape as the other PreToolUse hooks.
deny() {
  "$PY" -c '
import json, sys
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": sys.argv[1],
    }
}))
' "$1"
  exit 0
}

# Stage 1 — the Write tool is denied unconditionally, no matter what it's writing.
[ "$TOOL" = "Write" ] && deny "The Write tool is blocked by policy."

# Stage 2 — Bash is allowed in general, but a command that uses `cat` together
# with a redirect or heredoc (">"  or "<<") is recognized as "writing a file
# via cat" and denied too. Everything else Bash can do is still untouched.
if [ "$TOOL" = "Bash" ]; then
  CMD=$("$PY" -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_input", {}).get("command") or "")
' <<<"$INPUT")

  echo "$CMD" | grep -qE '\bcat\b.*(<<|>)' && \
    deny "Blocked by hook: using 'cat' to write a file is not allowed."
fi

# Nothing matched above — allow. This hook only recognizes `cat`; it makes no
# attempt to enumerate every other way a command could write to a file.
exit 0
