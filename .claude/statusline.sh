#!/usr/bin/env bash
# Claude Code passes a JSON blob on stdin; we only need a couple of fields.
input=$(cat)
model=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('model',{}).get('display_name','?'))" 2>/dev/null)
dir=$(basename "$(pwd)")
printf 'PERMS-LAB | %s | dir:%s | env:%s' "$model" "$dir" "${LAB_ENV:-unset}"
