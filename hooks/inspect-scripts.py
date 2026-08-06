#!/usr/bin/env python3
"""
inspect-script.py  --  a PreToolUse hook that blocks secret leaks.

Registered on the "Bash" matcher, so Claude Code runs this BEFORE every Bash
command and hands us a JSON object describing it.

WHY THIS HOOK EXISTS (the Part 15 problem):
    A permission "deny" rule can only read the COMMAND STRING. So it can stop
        cat .env
    because the word ".env" is right there. But it is powerless against
        python3 scripts/leak.py
    because that command names no secret at all -- the secret is read INSIDE
    the script. A permission rule cannot open that file. A hook can.

HOW A PreToolUse HOOK ANSWERS CLAUDE CODE (two options):
    1. JSON on stdout : {"hookSpecificOutput": {"permissionDecision": "deny", ...}}
    2. EXIT CODE      : this file uses this one --
           exit 2  ->  BLOCK  (stderr is sent to Claude)
           exit 0  ->  ALLOW  (stdout is just a note in the transcript)
           exit 1  ->  the hook CRASHED; the command RUNS ANYWAY (does NOT block)

Point the hook config at this file:
    "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/inspect-script.py"
"""

import json
import os
import re
import sys

# What counts as a "secret": credential filenames or path fragments.
SECRETS = re.compile(r"\.env|secrets/|api-keys|id_rsa")


def deny(reason):
    """BLOCK the command. stderr carries the reason, and exit 2 is the signal
    that actually stops the command and hands that reason to Claude."""
    print(reason, file=sys.stderr)
    sys.exit(2)


def allow(note):
    """ALLOW the command. exit 0 is the decision; stdout is only a note for the
    person watching the transcript -- Claude does not act on it."""
    print(note)
    sys.exit(0)


# ---------------------------------------------------------------------- #
# 1. READ the JSON object from stdin and pull out the command string.    #
#    e.g. "python3 scripts/leak.py"                                       #
#    `or "{}"` guards against empty stdin: a crash would exit 1, and      #
#    exit 1 does NOT block, so a crash would silently let the command run.#
# ---------------------------------------------------------------------- #
payload = json.loads(sys.stdin.read() or "{}")
command = payload.get("tool_input", {}).get("command") or ""

# ---------------------------------------------------------------------- #
# 2. FIRST CHECK: does the command itself name a secret file?            #
#    e.g. "cat .env" -- this is the same job a permission deny rule does. #
# ---------------------------------------------------------------------- #
if SECRETS.search(command):
    deny("Blocked: the command names a credential file.")

# ---------------------------------------------------------------------- #
# 3. THE REAL FIX: if the command runs a script, open it and look inside. #
#    This is the part a permission rule cannot do -- only a hook can.     #
# ---------------------------------------------------------------------- #
for word in command.split():
    # Only inspect words that look like a script file; skip flags and args.
    if not word.endswith((".py", ".sh")):
        continue

    # The word may be a path relative to the project root or to the hook's
    # current directory -- try both and use whichever file actually exists.
    path = word if os.path.isfile(word) else os.path.join(
        os.environ.get("CLAUDE_PROJECT_DIR", "."), word)
    if not os.path.isfile(path):
        continue

    # Read the script's own source and scan it for the same secret patterns.
    with open(path, errors="ignore") as fh:
        lines = fh.read().splitlines()

    hits = [f"{n}:{text}" for n, text in enumerate(lines, 1) if SECRETS.search(text)]
    if hits:
        # Prefer a hit that looks like real code (has "(" or "=") over a comment,
        # so the message points at something useful. Take the last such line.
        code_hits = [h for h in hits if "(" in h or "=" in h]
        line = (code_hits or hits)[-1][:80]
        deny(f"Blocked: {word} reads a credential file. Line {line}")

# ---------------------------------------------------------------------- #
# 4. Nothing matched -- let the command run.                             #
# ---------------------------------------------------------------------- #
allow(f"Approved: {command}")
