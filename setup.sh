#!/usr/bin/env bash
# One-time lab setup. Safe to re-run.
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED="$(dirname "$REPO")/cc-shared"

echo "==> repo   : $REPO"
echo "==> shared : $SHARED   (deliberately OUTSIDE the repo)"

# 1. The directory that lives outside the working directory.
#    Labs 1, 2 and 3 all use this as their "outside the boundary" target.
mkdir -p "$SHARED"
cat > "$SHARED/style-guide.md" <<'EOF'
# Shared Style Guide

This file lives OUTSIDE the project directory and outside the git repo.

Lab 1  the agent edits this freely
Lab 2  Bash is blocked from writing here, but the Edit tool still can
Lab 3  this directory does not exist inside the microVM
EOF

# 2. A decoy credential in the home directory, so sandbox.credentials
#    demos never have to point at a student's real ~/.ssh.
mkdir -p "$HOME/.lab-secrets"
echo "FAKE-PRIVATE-KEY-training-only-not-a-real-key" > "$HOME/.lab-secrets/fake_id_rsa"

# 3. Lab 3 (sbx --clone) needs a normal git repo on a 'main' branch.
cd "$REPO"
git rev-parse --git-dir >/dev/null 2>&1 || git init -q
git symbolic-ref -q HEAD >/dev/null && git branch -M main 2>/dev/null || true

echo
echo "Setup complete."
echo
echo "  Start Claude Code from the repo root:"
echo "     cd $REPO && claude"
echo
echo "  Accept the workspace trust dialog, or every allow rule is ignored."
echo
