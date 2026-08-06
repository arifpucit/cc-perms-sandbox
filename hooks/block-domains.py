#!/usr/bin/env python3
"""
block-domains.py  --  a PreToolUse hook covering TWO tools at once.

Registered on the "Bash|WebFetch" matcher, so Claude Code runs this BEFORE a
Bash command AND before a WebFetch, handing us a JSON object on stdin.

WHY ONE HOOK FOR BOTH TOOLS (the Part 16 problem):
    /sandbox blocked "curl https://arifbutt.me", but then the WebFetch tool
    reached the same site anyway -- because the sandbox only wraps Bash. A hook
    isn't limited to one tool: a single "Bash|WebFetch" matcher lets us apply
    the SAME domain check to both paths out to the network.

THE ONE WRINKLE:
    Each tool hides the thing we care about under a different JSON field --
        WebFetch -> tool_input.url
        Bash     -> tool_input.command   (a string that may contain a URL)
    so we read the right field per tool, then run one identical check.

HOW IT ANSWERS CLAUDE CODE:
    JSON-output deny shape on stdout, then exit 0. Printing nothing on stdout is
    how a PreToolUse hook says "allow".

Because the file is already Python, there's no python3-vs-python juggling like
the bash version needed -- the shebang picks the interpreter.

Point the hook config at this file:
    "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/block-domain.py"
"""

import json
import re
import sys

# The domain we refuse to reach, however we reach it. It's a regex, so the "."
# is escaped to mean a literal dot.
DENIED = r"arifbutt\.me"


def deny(reason):
    """BLOCK the tool call using the JSON deny shape, then exit 0. With JSON
    output, exit 0 plus this object is what blocks -- not exit 2."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


# ---------------------------------------------------------------------- #
# 1. READ the JSON object from stdin and see which tool triggered us.     #
#    `or "{}"` guards against empty stdin so the hook can't crash.        #
# ---------------------------------------------------------------------- #
payload = json.loads(sys.stdin.read() or "{}")
tool = payload.get("tool_name") or ""
tool_input = payload.get("tool_input", {})

# ---------------------------------------------------------------------- #
# 2. PICK THE RIGHT FIELD per tool: WebFetch keeps a "url", Bash keeps a   #
#    "command". Everything downstream treats them the same way.           #
# ---------------------------------------------------------------------- #
if tool == "WebFetch":
    text = tool_input.get("url") or ""
else:
    text = tool_input.get("command") or ""

# ---------------------------------------------------------------------- #
# 3. ONE CHECK for both tools -- that's the whole point of matching both  #
#    with a single hook. If the denied domain appears, block it.          #
# ---------------------------------------------------------------------- #
if re.search(DENIED, text):
    deny(f"Blocked by hook: that domain is on the deny list. Tool was {tool}.")

# ---------------------------------------------------------------------- #
# 4. No match -- allow. Printing nothing on stdout is how a PreToolUse    #
#    hook says "allow".                                                    #
# ---------------------------------------------------------------------- #
sys.exit(0)
