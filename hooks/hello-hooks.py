#!/usr/bin/env python3
import json, sys

# Loads the JSON object sent by Claude Code in a variable named data
data = json.load(sys.stdin)

# Build a human-readable message showing the whole object.
message = "Hook fired! Claude Code sent me this JSON:\n" + json.dumps(data, indent=2)

# Hand it back on two separate channels, because they reach different audiences:
#   "additionalContext" -> injected into CLAUDE's context as a silent system, never renders in the UI.
print(json.dumps({
    "systemMessage": message, # the USER sees this in the terminal UI
    "hookSpecificOutput": {            #  a nested box for event-specific fields
        "hookEventName": "PreToolUse", #  which event this reply is for
        "additionalContext": message,  #  text CLAUDE sees, silently
    },
}))
sys.exit(0) #  exit code 0 = "all good, carry on"

