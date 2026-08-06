#!/usr/bin/env python3
import json, sys

# Claude Code sends a JSON object about the pending action on stdin.
data = json.load(sys.stdin)

# Build a human-readable message showing the whole object.
message = "Hook fired! Claude Code sent me this JSON:\n" + json.dumps(data, indent=2)

# Hand it back on two separate channels, because they reach different audiences:
#   "systemMessage"     -> the USER sees this in the terminal UI.
#   "additionalContext" -> injected into CLAUDE's context as a silent system, never renders in the UI.
print(json.dumps({
    "systemMessage": message,
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": message,
    },
}))
sys.exit(0)

