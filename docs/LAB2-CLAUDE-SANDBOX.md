# Lab 2 — Sandboxing with Claude Code's `/sandbox`

**Slides 5–8** · **Prerequisite:** Lab 1 (permissions) · **Platform:** macOS (Seatbelt, nothing to install)

The sentence Lab 1 ended on:

> Permission rules are string matching, not a security boundary. A boundary needs the OS.

This lab hands the job to the OS. The sentence it ends on:

> The OS boundary is real — but it is drawn around Bash, not around the agent.

Which is what sets up Lab 3.

| Section | Slide | Teaches |
|---|---|---|
| 0 | 5 | Re-prove the gap, sandbox OFF |
| 1 | 8 | `/sandbox`: turn it on, the two modes |
| 2 | 5, 7 | FILESYSTEM |
| 3 | 5, 7 | NETWORK |
| 4 | 5 | PROCESS |
| 5 | 7 | What is **outside** the box |
| 6 | 8 | Tuning: `allowWrite`, `denyRead`, `credentials`, the escape hatch |
| 7 | 6 | Where this sits on the spectrum → Lab 3 |

---

## Lab 0 — The gap, one more time (sandbox OFF)

Start Claude Code from the repo root. Confirm the sandbox is off with `/sandbox` (Mode tab), then:

```
Run scripts/fs_probe.py with python and show me the whole table.
```

Every row says `OK`. Writes land outside the project, in your home directory, and into `.claude/settings.json` itself. Reads pull `.env` despite the `deny: Read(./.env)` rule from Lab 1.

```
Now run scripts/exfil.py.
```

It collects both fake credential files and ships them to `example.com`. **This is the slide-5 code block, running.** One allow rule — `Bash(python *)` — bought all of it.

> Put the `fs_probe` table on screen and leave it there. Every remaining section is a diff against it.

---

## Lab 1 — Turn it on

### 1.1 Tour the panel

```
/sandbox
```

Three tabs on macOS: **Mode**, **Overrides**, **Config**. (A **Dependencies** tab appears only on Linux when a package is missing — on macOS, Seatbelt is built in, so there is nothing to install.)

Choosing a mode writes to `.claude/settings.local.json` — this project only. To enable it everywhere, set `sandbox.enabled` in `~/.claude/settings.json`; to enforce it for a team, use managed settings.

### 1.2 Configure it by hand instead

So students see the keys, put this in `.claude/settings.local.json`:

```jsonc
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,   // auto-allow mode
    "failIfUnavailable": true           // fail closed, see warning below
  }
}
```

> ⚠️ **`failIfUnavailable` matters more than it looks.** It defaults to `false`, which means a sandbox that cannot start prints a warning and **runs your commands unsandboxed anyway**. Every demo below would then quietly "succeed" and teach the exact opposite lesson. Set it `true` for the lab.

Restart Claude Code. Confirm on the `/sandbox` **Config** tab that the resolved settings show `enabled: true`.

### 1.3 The two modes

| Mode | Setting | Sandboxed commands |
|---|---|---|
| auto-allow | `autoAllowBashIfSandboxed: true` | Run with no prompt |
| regular permissions | `autoAllowBashIfSandboxed: false` | Same walls, every prompt stays |

**Both enforce identical filesystem and network walls. The only difference is who approves.**

Demo it with the rule-free command from Lab 1:

```
Run the date command and tell me the output.
```

- Lab 1, every permission mode → prompted
- Now, auto-allow → runs silently

Flip `autoAllowBashIfSandboxed` to `false`, restart, run it again → prompts. Same boundary, different approver.

### 1.4 ⚠️ auto-allow is not "auto mode"

Students who did Lab 1 §3.4 will conflate these. They are unrelated and combinable:

| | Controls | What replaces the prompt |
|---|---|---|
| **auto-allow** (`/sandbox`) | What a Bash command can *access once it runs* | The sandbox boundary |
| **auto mode** (`Shift+Tab`) | *Whether* each tool call runs at all | A classifier that reviews actions |

Also worth recalling: auto **mode** drops `Bash(python *)` as a wildcarded interpreter. Auto-**allow** does not — it doesn't need to, because the walls hold regardless.

### 1.5 What still prompts in auto-allow

All four are already configured from Lab 1. Run them:

```
Show me .env using cat.              → deny rule. Blocked, sandbox or not.
Push the current branch to origin.   → ask rule. Still prompts.
Delete everything in my home dir.    → rm targeting ~. Circuit breaker, still prompts.
```

Plus: the first request to a **new network domain** prompts, and **plan mode** is not widened by auto-allow.

---

## Lab 2 — FILESYSTEM

```
Run scripts/fs_probe.py again and show me the table.
```

Diff it against Lab 0:

| Target | Before | After | Why |
|---|---|---|---|
| inside working directory | OK | **OK** | Default write scope |
| session `$TMPDIR` | OK | **OK** | Also writable; note `$TMPDIR` now points somewhere new |
| `../cc-shared/` | OK | **BLOCKED** | Outside the working directory |
| home directory | OK | **BLOCKED** | `~/.bashrc` and friends are exactly the target this protects |
| `.claude/settings.json` | OK | **BLOCKED** | See below |
| reading `.env` | OK | **OK** | See below |
| reading `~/.lab-secrets/` | OK | **OK** | See below |

### 2.1 The two rows that teach the most

**`.claude/settings.json` is *inside* the working directory and still blocked.** The sandbox denies writes to Claude Code's settings files at every scope. A sandboxed command cannot rewrite its own policy — otherwise the first thing a compromised command would do is widen the walls.

**Reads stayed wide open.** This surprises everyone. The default read policy is *the entire machine* minus a few denied paths. That includes `~/.aws/credentials` and `~/.ssh/`. Section 6 closes it.

### 2.2 The Lab 1 callback

```
Run: python -c "open('../cc-shared/style-guide.md','a').write('\nsilent\n')"
```

In Lab 1 this ran with **no prompt** and changed a file outside the project. Now it dies at the syscall. Same command, same allow rule, same permission mode — different boundary.

```bash
cat ../cc-shared/style-guide.md   # unchanged
```

---

## Lab 3 — NETWORK

### 3.1 Egress is refused

```
Run scripts/exfil.py.
```

The files are still **COLLECTED** — reads are open — but egress is **BLOCKED**. Nothing is pre-allowed by default.

> Point at this explicitly: the read succeeded and it did not matter. Exfiltration needs both halves.

### 3.2 The prompt, then the allowlist

```
Run: python scripts/exfil.py pypi.org
```

The first request to a new host **prompts**. Approve it, and that host stays allowed for the rest of the session. Pre-allow instead:

```jsonc
"sandbox": {
  "network": {
    "allowedDomains": ["pypi.org", "*.pythonhosted.org"],
    "deniedDomains": ["example.com"]
  }
}
```

`deniedDomains` blocks a host even when a broader `allowedDomains` wildcard would permit it.

### 3.3 The caveat that belongs on a slide

The built-in proxy decides from the **client-supplied hostname** and does not terminate or inspect TLS by default. Allowing something broad like `github.com` creates a viable exfiltration path — domain fronting reaches hosts outside your allowlist. `network.tlsTerminate` exists but adds credential masking, not content filtering.

**The network wall is an allowlist of names, not an inspection of contents.**

---

## Lab 4 — PROCESS

```
Run scripts/spawn.py.
```

Three rungs — the python process, a `bash` child, a python grandchild — all attempting the same forbidden write. With the sandbox on, **all three are blocked**. Children inherit the boundary; escaping is not one `subprocess` call away.

### 4.1 Apple Events (macOS only)

```
Run: osascript -e 'tell application "Finder" to activate'
```

Fails with error `-600`. The macOS sandbox blocks Apple Events by default, because otherwise a sandboxed command could launch other applications *unsandboxed* with no prompt. `allowAppleEvents: true` lifts it — but only from user, managed, or CLI settings; project settings are ignored for that key.

---

## Lab 5 — What is OUTSIDE the box

This is the section Lab 3 depends on.

### 5.1 The Edit tool walks straight past the wall

Sandbox still on, auto-allow still on:

```
Use your Edit tool to append a line to ../cc-shared/style-guide.md
saying "written by the Edit tool".
```

⏸️ Prompts (outside the working directory). **Approve it.** ✅ It works.

```bash
cat ../cc-shared/style-guide.md
```

The file the *Bash* sandbox refused to touch two sections ago just changed — because **Read, Edit and Write do not run through the sandbox at all.** They use the permission system directly.

### 5.2 The full boundary map

| Inside the box | Outside the box |
|---|---|
| Bash commands Claude runs | Read, Edit, Write — permission rules only |
| Every child process they spawn | MCP servers |
| Bash commands inside subagents | Hooks and the status line |
| | Computer use, on your real desktop |

### 5.3 The two layers guard different doors

Worth stating flatly, because it is genuinely counter-intuitive:

- `permissions.deny: Read(./.env)` blocks Claude's **Read tool** and recognized shell reads — but not a `python` subprocess.
- `sandbox.filesystem.denyRead` blocks **subprocesses** — but does *not* block Claude's Read tool.

Neither is redundant. Neither is sufficient. This is what slide 3 means by "used together, not instead of each other."

**And the conclusion that follows:** the Bash sandbox alone is not enough for an unattended run. → Lab 3.

---

## Lab 6 — Tuning

### 6.1 Widen deliberately

```jsonc
"sandbox": { "filesystem": { "allowWrite": ["../cc-shared", "/tmp/build"] } }
```

Re-run `fs_probe.py` → the `../cc-shared/` row goes green again. Note the path syntax **differs from permission rules**: here `/tmp/build` is a genuine absolute path, and no prefix means relative to the project root.

### 6.2 Close the reads

```jsonc
"sandbox": {
  "filesystem": { "denyRead": ["~/"], "allowRead": ["."] },
  "credentials": {
    "files":   [{ "path": "~/.lab-secrets", "mode": "deny" }],
    "envVars": [{ "name": "LAB_TOKEN", "mode": "deny" }]
  }
}
```

Re-run `fs_probe.py`:
- `~/.lab-secrets/fake_id_rsa` → **BLOCKED**
- `LAB_TOKEN` → **not set in this process** (unset before each sandboxed command)
- project files → still readable, because the narrower `allowRead: ["."]` re-opens that part of the denied region

Overlap rule: **the more specific path wins.** `denyRead: ["~/"]` + `allowRead: ["~/projects"]` opens just that subtree; `allowRead: ["~/"]` + `denyRead: ["~/.env"]` keeps that one file shut. A broad allow can never silently re-expose a named secret.

> `"mode": "mask"` (sentinel value, real credential injected by the proxy on the way out) needs `network.tlsTerminate` **and** is ignored from project settings — it only works from `~/.claude/settings.json` or managed settings. Mention it; don't try to demo it from the repo.

### 6.3 The escape hatch, and closing it

When a command fails because of the sandbox, Claude may retry it with `dangerouslyDisableSandbox`. That retry runs outside the box and goes back through the normal permission flow — so you get a prompt, not silence.

```
Write "hello" into ../cc-shared/escape.txt however you can.
```

Watch it fail, then retry unsandboxed and prompt. Now close it:

```jsonc
"sandbox": { "allowUnsandboxedCommands": false }
```

The parameter is now ignored entirely — the Overrides tab calls this **Strict sandbox mode**. Commands must run sandboxed or be listed in `excludedCommands`.

### 6.4 `excludedCommands`

```jsonc
"sandbox": { "excludedCommands": ["docker *"] }
```

For tools structurally incompatible with the sandbox — `docker` needs the host socket; Go-based CLIs like `gh`, `gcloud` and `terraform` can fail TLS verification under Seatbelt. Excluded commands are not unprotected, just handled by the permission flow instead.

**Keep this list short.** It has no managed-only lockdown, so any developer can append to it.

---

## Lab 7 — Where this sits (slide 6)

Prove the boundary is a real OS primitive, not a policy check: every block you saw was the kernel refusing a syscall, with `Operation not permitted` coming from Seatbelt, not from Claude Code declining.

Then place it on the spectrum:

| | Isolates | Still shares |
|---|---|---|
| **Process sandbox** ← you are here | One process and its children | The host kernel, and your whole `~` for reads |
| Container | A userspace | The host kernel |
| **MicroVM** ← Lab 3 | A whole OS on virtual hardware | Nothing |
| VM | A whole OS | Nothing |
| Remote/hosted | Someone else's machine | Nothing |

The honest limits of the column you just configured:

1. It stops at Bash. Read, Edit, Write, MCP and hooks are outside it.
2. Reads default to your entire machine.
3. The network proxy matches hostnames without inspecting TLS.
4. `allowUnsandboxedCommands` defaults to leaving the escape hatch open.

> **Lab 3:** what if the boundary went around the *agent* instead of around its commands?

---

## Instructor notes

| Symptom | Cause |
|---|---|
| Every demo passes with the sandbox "on" | `failIfUnavailable` was left at `false` and the sandbox silently didn't start |
| `/sandbox` shows only a Dependencies tab | Linux without `bubblewrap`/`socat` — shouldn't happen on macOS |
| `date` prompts in auto-allow | `autoAllowBashIfSandboxed` is `false`, or you're in plan mode |
| Writes to `../cc-shared` still work | An `allowWrite` entry from §6.1 is still in the file |
| `denyRead: ["~/"]` broke everything | You need the paired `allowRead: ["."]`, and it must live in **project** settings for `.` to resolve to the project root |

**Reset:**
```bash
cd cc-perms-sandbox && git checkout -- . && git clean -fd
rm -f ../cc-shared/probe-outside.txt ../cc-shared/spawn-escape.txt ~/.lab-probe-home.txt
```
