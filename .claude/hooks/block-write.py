#!/usr/bin/env python3
"""
block-writes.py  --  a PreToolUse hook (Stage 2).

Registered on the "Write|Bash" matcher, so Claude Code runs this BEFORE the
Write tool AND BEFORE every Bash command, handing us a JSON object on stdin.

Deliberately incomplete on purpose -- see docs/LAB4-HOOKS.md 4.1 for what this
is meant to demonstrate.

    Stage 1: block the Write tool outright.
    Stage 2 (this version): ALSO block Bash commands that use `cat` to write a
             file (with a redirect ">" or a heredoc "<<").

HOW THIS HOOK ANSWERS CLAUDE CODE:
    It uses the JSON-output form (NOT exit codes) -- the same deny shape as the
    other PreToolUse hooks:
        {"hookSpecificOutput": {"permissionDecision": "deny", ...}}
    printed on stdout with exit 0. (The sibling inspect-script.py shows the
    other way: exit 2.) To ALLOW, this hook just exits 0 with no JSON -- that
    means "no decision", so the normal permission flow applies.

Because the file is already Python, there's no python3-vs-python juggling like
the bash version needed -- the shebang picks the interpreter.

Point the hook config at this file:
    "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/block-writes.py"
"""

import json
import re
import sys


def deny(reason):
    """BLOCK the tool call using the JSON deny shape. We print the decision on
    stdout and exit 0 -- with JSON output, exit 0 plus this object is what
    blocks, not exit 2."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


# ---------------------------------------------------------------------- #
# 1. READ the JSON object from stdin and pull out which tool is running.  #
#    `or "{}"` guards against empty stdin so the hook can't crash.        #
# ---------------------------------------------------------------------- #
payload = json.loads(sys.stdin.read() or "{}")
tool = payload.get("tool_name") or ""

# ---------------------------------------------------------------------- #
# 2. STAGE 1: the Write tool is denied unconditionally, whatever it writes.
# ---------------------------------------------------------------------- #
if tool == "Write":
    deny("The Write tool is blocked by policy.")

# ---------------------------------------------------------------------- #
# 3. STAGE 2: Bash is allowed in general, but a command that uses `cat`   #
#    together with a redirect (">") or heredoc ("<<") is recognized as    #
#    "writing a file via cat" and denied too. Every other Bash command    #
#    is still untouched.                                                  #
# ---------------------------------------------------------------------- #
if tool == "Bash":
    command = payload.get("tool_input", {}).get("command") or ""
    if re.search(r"\bcat\b.*(<<|>)", command):
        deny("Blocked by hook: using 'cat' to write a file is not allowed.")

# ---------------------------------------------------------------------- #
# 4. Nothing matched -- allow. This hook only recognizes `cat`; it makes  #
#    no attempt to enumerate every other way a command could write a file.#
# ---------------------------------------------------------------------- #
sys.exit(0)
