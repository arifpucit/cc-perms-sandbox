"""Process dimension probe.

A sandbox that only constrained the process you launched would be
useless -- escaping would be one subprocess call away. This checks
whether the walls follow children down the process tree.

Each rung spawns the next and tries the same forbidden write.
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
TARGET = PROJECT.parent / "cc-shared" / "spawn-escape.txt"

print("=" * 68)
print(" PROCESS PROBE")
print("=" * 68)
print(f"  forbidden target : {TARGET}")
print(f"  my pid           : {os.getpid()}\n")


def verdict(level, ok, detail=""):
    tag = "WROTE  " if ok else "BLOCKED"
    print(f"  [{tag}] level {level}: {detail}")


# ---- Level 0: this process ----
try:
    with open(TARGET, "a") as fh:
        fh.write("level 0 (python)\n")
    verdict(0, True, "the python process itself")
except Exception as exc:
    verdict(0, False, f"the python process itself -- {type(exc).__name__}")

# ---- Level 1: a shell child ----
child = subprocess.run(
    ["bash", "-c", f'echo "level 1 (bash child)" >> "{TARGET}"'],
    capture_output=True,
    text=True,
)
verdict(1, child.returncode == 0,
        "bash child via subprocess -- " + (child.stderr.strip() or "no error"))

# ---- Level 2: a grandchild, one more level down ----
inner = (f'import pathlib; fh = pathlib.Path(r"{TARGET}").open("a"); '
         f'print("level 2 (python grandchild)", file=fh)')
grand = subprocess.run(
    ["bash", "-c", f'{sys.executable} -c {inner!r}'],
    capture_output=True,
    text=True,
)
tail = (grand.stderr.strip().splitlines() or ["no error"])[-1]
verdict(2, grand.returncode == 0, f"python grandchild via bash -- {tail}")

print()
if TARGET.exists():
    print(f"  Result: {TARGET.name} EXISTS. Contents:")
    for line in TARGET.read_text().splitlines():
        print(f"    {line}")
    print("\n  No boundary here. Any level could write outside the project.")
else:
    print("  Result: the file was never created.")
    print("  Every level inherited the same walls. Children cannot escape.")
print()
