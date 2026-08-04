#!/usr/bin/env bash
# Fires before every Bash command.
# Part 15 problem: the deny rules stop "cat .env", but not "python3 scripts/leak.py",
# because that command string does not contain the word .env anywhere.
# A permission rule can only read the command. This hook opens the script and reads THAT.

# Prefer python3 (Mac/Linux default); fall back to python (e.g. some Windows installs).
command -v python3 >/dev/null 2>&1 && PY=python3 || PY=python

# Regex of anything we consider a "secret" — filenames or path fragments only.
SECRETS='(\.env|secrets/|api-keys|id_rsa)'

# Claude Code sends one JSON object on stdin describing the tool call. Read it all in.
INPUT=$(cat)
# Pull out just the command string, e.g. "python3 scripts/leak.py".
CMD=$("$PY" -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_input", {}).get("command") or "")
' <<<"$INPUT")

# Prints the JSON shape PreToolUse hooks use to block a tool call, then exits.
# exit 0 here is correct even on a deny — the *JSON payload* is what blocks the
# tool, not the exit code (that matters for Stop hooks, not this one).
deny() {
  "$PY" -c '
import json, sys
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": sys.argv[1],
    }
}))
' "$1"
  exit 0
}

# 1. the command itself names a secret file
# e.g. "cat .env" — same job a plain permission deny rule already does.
grep -qE "$SECRETS" <<<"$CMD" && deny "Blocked: the command names a credential file."

# 2. the command runs a script - open it and look inside
# This is the actual fix: a permission rule can't do this part, only a hook can.
for WORD in $CMD; do
  # Only bother inspecting words that look like a script file; skip flags/args.
  case "$WORD" in *.py|*.sh) ;; *) continue ;; esac

  # The word might be a path relative to the project root, or already relative
  # to wherever this hook's cwd is — try both and use whichever actually exists.
  FILE="${CLAUDE_PROJECT_DIR:-.}/$WORD"
  [ -f "$WORD" ] && FILE="$WORD"
  [ -f "$FILE" ] || continue

  # Read the script's own source for the same secret patterns.
  if grep -qE "$SECRETS" "$FILE"; then
    # Grab the last matching line that looks like real code (has "(" or "=")
    # so the deny message can point at something useful instead of a comment.
    LINE=$(grep -nE "$SECRETS" "$FILE" | grep -E '[(=]' | tail -n 1 | cut -c1-80)
    deny "Blocked: $WORD reads a credential file. Line $LINE"
  fi
done

# Nothing matched — let the command run.
exit 0
