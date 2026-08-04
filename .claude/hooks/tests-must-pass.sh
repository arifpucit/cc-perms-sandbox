#!/usr/bin/env bash
# Fires when Claude tries to END ITS TURN.
# Neither permissions nor the sandbox can do this - they only see tool calls.

# Prefer python3 (Mac/Linux default); fall back to python (e.g. some Windows installs).
command -v python3 >/dev/null 2>&1 && PY=python3 || PY=python

# Claude Code sends one JSON object on stdin, this time describing the Stop event.
INPUT=$(cat)

# already fired once this turn? let it finish, or we loop forever
# When this hook blocks a Stop event, Claude Code immediately re-fires Stop
# after Claude's next attempt to finish. stop_hook_active is true on that
# second firing, so this line is the loop's exit condition. Comment it out
# (see LAB4-HOOKS.md §3.4) and every future finish attempt loops forever.
STOP_ACTIVE=$("$PY" -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print("true" if d.get("stop_hook_active") else "false")
' <<<"$INPUT")
[ "$STOP_ACTIVE" = "true" ] && exit 0

# Run the suite from the project root, not wherever this hook happened to launch.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
# Capture pytest's combined stdout+stderr. If it exits 0 (all green), we're done.
OUT=$(pytest -q 2>&1) && exit 0

# pytest failed — build a block decision. Unlike PreToolUse's "permissionDecision"
# shape, Stop hooks use {"decision":"block","reason":...}. "reason" is written
# FOR CLAUDE — it lands in the transcript as the explanation Claude reads and
# acts on, which is why we paste real pytest output instead of a generic message.
REASON="Tests are failing. Fix them before you finish:

$(tail -n 10 <<<"$OUT")"

"$PY" -c '
import json, sys
print(json.dumps({"decision": "block", "reason": sys.argv[1]}))
' "$REASON"
exit 0
