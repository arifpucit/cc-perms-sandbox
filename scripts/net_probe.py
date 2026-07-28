"""Network layer probe -- for Lab 3 (sbx).

sbx claims four things about the network:
  1. Only domains your policy lists resolve at all
  2. DNS goes through the proxy and obeys the same policy
  3. Raw TCP, UDP and ICMP are blocked outright
  4. There is no route to your host's localhost, or to another sandbox

This checks all four. Run it on the host first (everything passes),
then inside the sandbox (watch them fall over one by one).

Usage:
    python scripts/net_probe.py [domain-to-test] [host-port]
"""
import socket
import subprocess
import sys
import urllib.error
import urllib.request

DOMAIN = sys.argv[1] if len(sys.argv) > 1 else "example.com"
HOST_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
TIMEOUT = 6


def check(label, fn):
    try:
        detail = fn()
        print(f"  [ALLOWED] {label}")
        if detail:
            print(f"            {detail}")
    except Exception as exc:
        print(f"  [BLOCKED] {label}")
        print(f"            {type(exc).__name__}: {str(exc)[:90]}")


print("=" * 68)
print(" NETWORK LAYER PROBE")
print("=" * 68)

print("\n--- 1. DNS resolution (does the name resolve at all?) ---")
check(f"resolve {DOMAIN}", lambda: socket.gethostbyname(DOMAIN))
check("resolve a domain nobody allowlisted (example.invalid)",
      lambda: socket.gethostbyname("example.invalid"))

print("\n--- 2. HTTPS through the proxy ---")


def https():
    with urllib.request.urlopen(f"https://{DOMAIN}/", timeout=TIMEOUT) as r:
        return f"HTTP {r.status}"


check(f"GET https://{DOMAIN}/", https)

print("\n--- 3. Raw TCP on a non-HTTP port ---")


def raw_tcp():
    s = socket.create_connection((DOMAIN, 22), timeout=TIMEOUT)
    s.close()
    return "socket opened on port 22"


check(f"raw TCP to {DOMAIN}:22", raw_tcp)

print("\n--- 4. ICMP (ping) ---")


def ping():
    flag = "-w" if sys.platform.startswith("win") else "-W"
    try:
        out = subprocess.run(["ping", "-c", "1", flag, "3", DOMAIN],
                             capture_output=True, text=True, timeout=TIMEOUT)
    except FileNotFoundError:
        return "SKIPPED -- no ping binary on this machine, not a block"
    if out.returncode != 0:
        raise OSError((out.stderr or out.stdout).strip()[:90] or "ping failed")
    return "echo reply received"


check(f"ping {DOMAIN}", ping)

print("\n--- 5. Route back to the host ---")


def host_localhost():
    with urllib.request.urlopen(f"http://127.0.0.1:{HOST_PORT}/", timeout=4) as r:
        return f"reached 127.0.0.1:{HOST_PORT}, HTTP {r.status}"


check(f"http://127.0.0.1:{HOST_PORT}/ (host web server)", host_localhost)


def host_internal():
    with urllib.request.urlopen(
            f"http://host.docker.internal:{HOST_PORT}/", timeout=4) as r:
        return f"reached host.docker.internal, HTTP {r.status}"


check(f"http://host.docker.internal:{HOST_PORT}/", host_internal)

print("\n  On the host, most of these pass. Inside a sandbox, the pattern")
print("  itself is the lesson: HTTP/HTTPS survives via the proxy, and")
print("  everything else -- raw sockets, ICMP, your localhost -- does not.\n")
