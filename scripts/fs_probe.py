"""Filesystem dimension probe.

Attempts a battery of reads and writes and reports what the OS allowed.
Run it with the sandbox OFF, then again with it ON, and diff the two tables.

Nothing here is clever. It is plain open() calls -- which is the point:
the permission layer sees the string "python scripts/fs_probe.py" and
nothing more. Only the kernel sees these syscalls.
"""
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
HOME = Path.home()
TMPDIR = os.environ.get("TMPDIR", "/tmp")

MARK = "written by fs_probe.py\n"


def try_write(label, path, restore=False):
    """Append to `path`. With restore=True, put the file back exactly as it
    was, so probing a real config file can never damage it."""
    original = None
    if restore:
        try:
            original = Path(path).read_bytes()
        except Exception:
            original = None
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as fh:
            fh.write(MARK)
        return label, "WROTE", str(path), ""
    except Exception as exc:
        return label, "BLOCKED", str(path), type(exc).__name__ + ": " + str(exc)
    finally:
        if restore and original is not None:
            try:
                Path(path).write_bytes(original)
            except Exception:
                pass


def try_read(label, path):
    try:
        data = Path(path).read_text()
        preview = data.strip().splitlines()[0][:40] if data.strip() else "(empty)"
        return label, "READ", str(path), preview
    except Exception as exc:
        return label, "BLOCKED", str(path), type(exc).__name__ + ": " + str(exc)


def report(rows, title):
    print(f"\n=== {title} ===")
    for label, verdict, path, detail in rows:
        icon = "OK     " if verdict in ("WROTE", "READ") else "BLOCKED"
        print(f"  [{icon}] {label}")
        print(f"            {path}")
        if detail:
            print(f"            {detail}")


print("=" * 68)
print(" FILESYSTEM PROBE")
print("=" * 68)
print(f"  cwd     : {Path.cwd()}")
print(f"  project : {PROJECT}")
print(f"  TMPDIR  : {TMPDIR}")

writes = [
    try_write("inside the working directory", PROJECT / "probe-inside.txt"),
    try_write("session temp directory", Path(TMPDIR) / "probe-tmp.txt"),
    try_write("sibling dir OUTSIDE the project", PROJECT.parent / "cc-shared" / "probe-outside.txt"),
    try_write("home directory", HOME / ".lab-probe-home.txt"),
    try_write("Claude Code's own policy file", PROJECT / ".claude" / "settings.json",
              restore=True),
]
report(writes, "WRITE ATTEMPTS")

reads = [
    try_read("project .env", PROJECT / ".env"),
    try_read("project secrets/", PROJECT / "secrets" / "api-keys.txt"),
    try_read("decoy key in home dir", HOME / ".lab-secrets" / "fake_id_rsa"),
]
report(reads, "READ ATTEMPTS")

print("\n=== ENVIRONMENT ===")
token = os.environ.get("LAB_TOKEN")
if token:
    print(f"  [OK     ] LAB_TOKEN is visible: {token}")
else:
    print("  [BLOCKED] LAB_TOKEN is not set in this process")

print("\nDone. Compare this table before and after enabling the sandbox.\n")
