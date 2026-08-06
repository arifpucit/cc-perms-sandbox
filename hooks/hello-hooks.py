#!/usr/bin/env python3
import json, sys

# Claude Code sends a JSON object about the pending action on stdin.
data = json.load(sys.stdin)

# Build a human-readable message showing the whole object.
message = "Hook fired! Claude Code sent me this JSON:\n" + json.dumps(data, indent=2)

# Hand it back via "systemMessage" so the USER sees it in the UI.
# On exit 0, stdout must contain ONLY this JSON object.
print(json.dumps({"systemMessage": message}))
sys.exit(0)
