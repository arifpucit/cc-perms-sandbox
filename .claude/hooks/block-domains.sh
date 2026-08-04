#!/usr/bin/env bash
# Fires before Bash AND before WebFetch.
# Part 16 problem: /sandbox blocked "curl https://arifbutt.me", then the WebFetch
# tool reached the same site, because the sandbox only wraps Bash.
# One matcher here covers both tools.

# Prefer python3 (Mac/Linux default); fall back to python (e.g. some Windows installs).
command -v python3 >/dev/null 2>&1 && PY=python3 || PY=python

DENIED='arifbutt\.me'

# Claude Code sends one JSON object on stdin describing the tool call.
INPUT=$(cat)
# Which tool triggered this hook? Could be "Bash" or "WebFetch" here (see the
# "Bash|WebFetch" matcher in the config), so we branch on it below.
TOOL=$("$PY" -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_name") or "")
' <<<"$INPUT")

# Each tool stores the thing we care about under a different JSON field:
# WebFetch has a "url", Bash has a "command" string that may contain a URL.
if [ "$TOOL" = "WebFetch" ]; then
  TEXT=$("$PY" -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_input", {}).get("url") or "")
' <<<"$INPUT")
else
  TEXT=$("$PY" -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_input", {}).get("command") or "")
' <<<"$INPUT")
fi

# Same check, same deny shape, regardless of which tool it came from —
# that's the whole point of matching both tools with one hook.
if grep -qE "$DENIED" <<<"$TEXT"; then
  "$PY" -c '
import json, sys
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": sys.argv[1],
    }
}))
' "Blocked by hook: that domain is on the deny list. Tool was $TOOL."
fi
# No match (or the deny JSON was already printed above) — either way, exit 0.
# Printing nothing on stdout is how a PreToolUse hook says "allow".
exit 0
