#!/usr/bin/env python3
"""
hello-hooks.py  --  a teaching hook for Claude Code.

Registered in settings.json as a PreToolUse hook on the "Bash" matcher, so
Claude Code runs THIS SCRIPT *before* it executes any Bash command.

The one idea to take away:

    Claude Code hands every hook a JSON object on standard input (stdin),
    and the hook answers back with JSON on standard output (stdout).

There are two ways to answer. Know both, and know why we use the second:

  1. EXIT CODE
        exit 0  ->  allow, and stdout goes to the DEBUG LOG ONLY
        exit 1  ->  non-blocking error; stderr goes to the DEBUG LOG ONLY
        exit 2  ->  block, and stderr IS sent back to Claude

     Note what this means: with exit codes, the only message a human ever
     sees on screen is the exit-2 one. Print a friendly banner and exit 0
     and it vanishes -- which is exactly the trap this lab used to fall into.

  2. JSON ON STDOUT  (what this script uses)
        {"systemMessage": "..."}  is DISPLAYED IN THE TERMINAL, every time,
        whatever the decision. That is the field that makes a hook visible.

     Blocking is then a data field rather than an exit status:
        hookSpecificOutput.permissionDecision = "deny"
     and the hook still exits 0, because the JSON carries the verdict.

One sharp edge worth saying out loud in class:

    permissionDecision "allow" does NOT mean "this is fine, carry on".
    It means AUTO-APPROVE -- it bypasses the normal permission system,
    including your own deny rules in settings.json. A hook that only wants
    to LOOK at commands must OMIT permissionDecision entirely, which is
    what the warn and allow branches below do.

Docs: https://code.claude.com/docs/en/hooks.md
"""

import json
import sys

# ---------------------------------------------------------------------- #
# 1. READ the JSON object that Claude Code sends us on stdin.            #
#    This is the whole point: the hook is handed structured context      #
#    about what Claude is about to do.                                    #
#                                                                         #
#    `or "{}"` keeps an empty stdin from crashing the hook. A hook that   #
#    crashes exits 1, and exit 1 does NOT block -- so a crashed hook      #
#    silently lets the command run.                                       #
# ---------------------------------------------------------------------- #
input_data = json.loads(sys.stdin.read() or "{}")

# ---------------------------------------------------------------------- #
# 2. PULL OUT the interesting fields so students can see the shape.      #
#    For a PreToolUse + Bash call, the command Claude wants to run        #
#    lives at  tool_input.command                                        #
# ---------------------------------------------------------------------- #
event   = input_data.get("hook_event_name", "?")          # e.g. "PreToolUse"
tool    = input_data.get("tool_name", "?")                # e.g. "Bash"
session = input_data.get("session_id", "?")
cwd     = input_data.get("cwd", "?")
command = input_data.get("tool_input", {}).get("command", "")

# ---------------------------------------------------------------------- #
# 3. BUILD the banner showing the whole object, so the class can see      #
#    exactly what Claude Code passed in. Nothing is printed yet --        #
#    every branch below sends it out via systemMessage.                   #
# ---------------------------------------------------------------------- #
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
    """Answer Claude Code with JSON on stdout, then exit 0.

    systemMessage is the field the human actually sees in the terminal, so
    the banner rides along with every verdict -- allowed, warned or blocked.

    decision is passed ONLY for the block case. Leaving it out is not
    laziness: an absent permissionDecision means "defer to the normal
    permission system", which is what an observer hook wants. Setting it to
    "allow" would auto-approve the command and skip your settings.json rules.
    """
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

# ---------------------------------------------------------------------- #
# 4a. BLOCK  ->  permissionDecision "deny". The command is prevented from #
#     running, and permissionDecisionReason is handed to Claude so it     #
#     knows why and can react.                                           #
#     Trigger it safely with:  echo blockme                              #
# ---------------------------------------------------------------------- #
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
