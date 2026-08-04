#!/usr/bin/env bash
# Reset the lab between sessions.
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED="$(dirname "$REPO")/cc-shared"
cd "$REPO"

git checkout -- . 2>/dev/null || true
git clean -fd -e .sbx 2>/dev/null || true

rm -f "$SHARED"/probe-outside.txt "$SHARED"/spawn-escape.txt "$SHARED"/escape.txt
rm -f "$HOME/.lab-probe-home.txt" probe-inside.txt
rm -f .git/hooks/pre-commit                      # Lab 3 direct-mount demo
rm -f hello.py                                   # Lab 4
git remote 2>/dev/null | grep '^sandbox-' | while read -r r; do git remote remove "$r"; done

# restore the shared file Lab 2 and 3 write into
bash "$REPO/setup.sh" >/dev/null

echo "Reset complete. Check .claude/settings.local.json for stray"
echo "'Yes, don't ask again' rules before the next session."
