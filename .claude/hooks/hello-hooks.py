#!/usr/bin/env python3
"""
hello-hooks.py  --  Claude Code runs THIS SCRIPT *before* it executes any Bash command.
    Claude Code hands every hook a JSON object on standard input (stdin),
    and the hook answers back with JSON on standard output (stdout).
    EXIT CODE
        exit 0  ->  allow, and stdout goes to the DEBUG LOG ONLY
        exit 1  ->  non-blocking error; stderr goes to the DEBUG LOG ONLY
        exit 2  ->  block, and stderr IS sent back to Claude
"""

import json
import sys


# 1. READ the JSON object that Claude Code sends us on stdin.
#    BUILD the banner showing the whole object, so the class can see
input_data = json.loads(sys.stdin.read() or "{}")
event   = input_data.get("hook_event_name", "?")          # e.g. "PreToolUse"
tool    = input_data.get("tool_name", "?")                # e.g. "Bash"
session = input_data.get("session_id", "?")
cwd     = input_data.get("cwd", "?")
command = input_data.get("tool_input", {}).get("command", "")

banner = (
    "\n================== hello-hooks fired ==================\n"
    f"event    : {event}\n"
    f"tool     : {tool}\n"
    f"session  : {str(session)[:8]}\n"
    f"cwd      : {cwd}\n"
    f"command  : {command!r}\n"
    "------- full JSON object received on stdin -------\n"
    f"{json.dumps(input_data, indent=2)}\n"
    "=======================================================\n"
)


def respond(verdict, decision=None, reason=None):
    hook_output = {"hookEventName": "PreToolUse"}
    if decision:
        hook_output["permissionDecision"] = decision
        hook_output["permissionDecisionReason"] = reason
    print(json.dumps({
        "systemMessage": banner + verdict,
        "hookSpecificOutput": hook_output,
    }))
    sys.exit(0)

lowered = command.lower()


#  BLOCK  ->  permissionDecision "deny".
for bad in ("blockme", "rm -rf", "mkfs", "shutdown"):
    if bad in lowered:
        reason = (
            f"BLOCKED by hello-hooks: matched '{bad}'. "
            f"This command is not allowed in the demo."
        )
        respond(reason, decision="deny", reason=reason)

# ---------------------------------------------------------------------- #
# 4b. WARN  ->  visible, but not blocking. No permissionDecision field,   #
#     so the normal permission system still gets its say; we have only    #
#     added a message on screen.                                         #
#     Trigger it safely with:  echo warnme                               #
# ---------------------------------------------------------------------- #
for risky in ("warnme", "curl", "wget", "sudo"):
    if risky in lowered:
        respond(
            f"WARNING from hello-hooks: matched '{risky}'. "
            f"Allowed, but flagged for your attention."
        )

# ---------------------------------------------------------------------- #
# 4c. ALLOW  ->  same shape as the warning: say something, decide nothing.#
#     Anything not matched above lands here, e.g.  git log --oneline      #
# ---------------------------------------------------------------------- #
respond("ALLOWED by hello-hooks: nothing suspicious in this command.")
