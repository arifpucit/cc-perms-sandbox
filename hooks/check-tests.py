#!/usr/bin/env python3
"""
check-tests.py  --  a Stop hook that refuses to finish while tests fail.

Registered on the "Stop" event, so Claude Code runs this when Claude tries to
END ITS TURN. Neither permissions nor the sandbox can do this -- they only see
tool calls, never the moment Claude decides it's done.

THE LOOP TRAP (read this before removing anything):
    When this hook blocks a Stop, Claude Code lets Claude try again, then fires
    Stop AGAIN. On that second firing stop_hook_active is true. Checking it and
    exiting early is the loop's ONLY exit condition. Remove that check (see
    LAB4-HOOKS.md 3.4) and every future finish attempt loops forever.

HOW A Stop HOOK ANSWERS CLAUDE CODE:
    Unlike PreToolUse's "permissionDecision" shape, Stop hooks use
        {"decision": "block", "reason": "..."}
    printed on stdout. The "reason" is written FOR CLAUDE -- it lands in the
    transcript as the explanation Claude reads and acts on, which is why we
    paste real pytest output instead of a generic message. Printing nothing and
    exiting 0 lets Claude finish.

Because the file is already Python, there's no python3-vs-python juggling like
the bash version needed -- the shebang picks the interpreter.

Point the hook config at this file:
    "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/check-tests.py"
"""

import json
import os
import subprocess
import sys

# ---------------------------------------------------------------------- #
# 1. READ the JSON object -- this time it describes the Stop event.       #
#    `or "{}"` guards against empty stdin so the hook can't crash.        #
# ---------------------------------------------------------------------- #
payload = json.loads(sys.stdin.read() or "{}")

# ---------------------------------------------------------------------- #
# 2. LOOP GUARD: if we already blocked once this turn, let Claude finish, #
#    otherwise we'd block forever. This is the exit condition -- keep it. #
# ---------------------------------------------------------------------- #
if payload.get("stop_hook_active"):
    sys.exit(0)

# ---------------------------------------------------------------------- #
# 3. Run the suite from the PROJECT ROOT, not wherever the hook launched. #
#    If we can't even cd there, don't hold Claude hostage -- allow.       #
# ---------------------------------------------------------------------- #
try:
    os.chdir(os.environ.get("CLAUDE_PROJECT_DIR", "."))
except OSError:
    sys.exit(0)

# ---------------------------------------------------------------------- #
# 4. Run pytest, capturing stdout+stderr together. All green -> allow.    #
# ---------------------------------------------------------------------- #
result = subprocess.run(
    ["pytest", "-q"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
if result.returncode == 0:
    sys.exit(0)

# ---------------------------------------------------------------------- #
# 5. Tests failed -- BLOCK the stop and hand Claude the last 10 lines of  #
#    real pytest output so it knows exactly what to fix.                  #
# ---------------------------------------------------------------------- #
last_lines = "\n".join(result.stdout.splitlines()[-10:])
reason = "Tests are failing. Fix them before you finish:\n" + last_lines
print(json.dumps({"decision": "block", "reason": reason}))
sys.exit(0)
