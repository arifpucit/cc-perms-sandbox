# Lab 3 — Sandboxing with `sbx` (Docker Sandboxes)

**Slides 11–13** · **Prerequisites:** Labs 1 and 2 · **Platform:** macOS Sonoma 14+, Apple silicon

Lab 2 ended here:

> The OS boundary is real — but it is drawn around Bash, not around the agent.

So the question slide 11 asks: **how do you put the agent itself inside a boundary, not just the commands it runs?**

| Section | Slide | Teaches |
|---|---|---|
| 0 | 13 | Install, login, secrets, preflight |
| 1 | 11 | First launch — and what `sbx ls` shows |
| 2 | 11 | The five isolation layers, one at a time |
| 3 | 12 | Direct mount: the danger that remains |
| 4 | 12 | Clone mode: the only mode the agent cannot write through |
| 5 | 12 | Network policy |
| 6 | 13 | Lifecycle and disposal |
| 7 | — | The whole course in one table |

> `sbx` moves fast. Run `sbx run --help` and `sbx create --help` before class — flags change. `--branch` is **deprecated**; `--clone` replaced it.

---

## Lab 0 — Setup

### 0.1 Preflight

| Platform | Requirement |
|---|---|
| macOS | Sonoma 14 or later, Apple silicon |
| Windows | Windows 11, Hypervisor Platform enabled |
| Ubuntu | 24.04+, KVM available, user in the `kvm` group |

**Docker Desktop is not required.** `sbx` is a separate binary — and it is `sbx`, not `docker sbx`.

```bash
brew install docker/tap/sbx
sbx version
sbx diagnose          # verifies virtualization before you're standing in front of a class
```

### 0.2 Login and network policy

```bash
sbx login
```

You pick a default network policy here:

| Policy | Behaviour |
|---|---|
| Open | No restrictions. Fastest, least instructive. |
| Balanced | Common dev domains (npm, PyPI, GitHub) allowed. |
| **Locked Down** | Nothing by default. **Choose this for the lab.** |

Locked Down makes section 5 self-demonstrating. Change any time with `sbx policy`.

### 0.3 Credentials stay on the host

```bash
sbx secret set -g anthropic
sbx secret ls
```

The value lands in your **host OS keychain**. A proxy adds the auth header on the way out, so the key is never a file or an environment variable inside the VM. You will verify that in §2.5.

### 0.4 Repo state

```bash
cd cc-perms-sandbox
git status              # must be clean
git branch              # must be main
echo '.sbx/' >> .gitignore
```

---

## Lab 1 — First launch

```bash
cd cc-perms-sandbox
sbx run --name lab claude .
```

The trailing `.` mounts the current directory as the workspace. First run pulls the agent image (1–2 minutes); later runs start in seconds.

Watch the banner. It reports the agent starting as:

```
claude --dangerously-skip-permissions
```

**Stop and sit on this.** In Lab 1 you taught that this flag removes the prompts that catch mistakes. Here it is the default, and that is not carelessness:

> The boundary is the hypervisor, not the model's judgment. The prompts are gone because a hardware boundary replaced them.

From a second terminal:

```bash
sbx ls
#  SANDBOX  AGENT   STATUS   WORKSPACE
#  lab      claude  running  ~/cc-perms-sandbox
```

---

## Lab 2 — The five isolation layers

Get a shell inside the VM so students see it directly:

```bash
sbx exec -it lab bash
```

### 2.1 HYPERVISOR — a separate kernel

```bash
uname -a          # a Linux kernel, on your macOS laptop
id                # you are root -- inside the VM only
ls /Users 2>&1    # your host home does not exist here
ps aux            # your host processes are invisible
```

A container escape gets you the host kernel. A microVM escape gets you nothing.

### 2.2 WORKSPACE — only your project is shared

```bash
ls /
ls ..             # the parent of the workspace
```

**`../cc-shared/` is not here.** Across three labs, the same directory:

| Lab | `../cc-shared/style-guide.md` |
|---|---|
| 1 | A python one-liner wrote to it silently |
| 2 | Bash blocked — but the Edit tool still wrote to it |
| 3 | **It does not exist** |

You can add it back deliberately, read-only:

```bash
sbx create claude . ../cc-shared:ro
```

That `PATH:ro` form is how extra workspaces are granted. Nothing is shared unless you name it.

### 2.3 NETWORK — its own stack

Exit the shell, then on the **host** start a server so there is something real to fail to reach:

```bash
python3 -m http.server 8000
```

Back inside the sandbox:

```bash
sbx exec -it lab bash
python scripts/net_probe.py example.com 8000
```

Under Locked Down, expect:

| Check | Result |
|---|---|
| DNS for a non-allowlisted domain | **BLOCKED** — DNS goes through the proxy and obeys the same policy |
| HTTPS to a non-allowlisted domain | **BLOCKED** |
| Raw TCP on port 22 | **BLOCKED** — only HTTP/HTTPS leave the VM |
| ICMP / ping | **BLOCKED** |
| `http://127.0.0.1:8000/` | **BLOCKED** — no route to your localhost |

Then the payoff:

```bash
python scripts/exfil.py
```

Files still **COLLECTED** — they are in the repo, and the repo is mounted — but egress refused. Even the agent's own vendor endpoints are subject to policy; the proxy makes no exception.

### 2.4 DOCKER ENGINE — a second daemon

```bash
docker info | head -20
docker build -t lab-demo .
docker images
```

This is why the repo now has a `Dockerfile`. The build runs against a Docker daemon **inside the VM**. Your host's daemon never sees it, and `docker build` has no path to your host socket. On the host, `docker images` will not show `lab-demo`.

### 2.5 CREDENTIALS — never inside the VM

```bash
env | grep -i -E 'anthropic|api_key'
ls ~/.claude 2>&1
cat ~/.claude.json 2>&1
```

No key. No host config. Two consequences worth naming:

- **The security win:** the credential is in your host keychain; a proxy injects it on the way out. There is nothing in the VM to steal.
- **The ergonomic cost:** your host `~/.claude` does not travel. Slash commands, skills, hooks, and your global `CLAUDE.md` are all absent. **A sandbox reads project-level configuration only** — so `.claude/settings.json` in the repo applies, and your user settings do not.

### 2.6 The Lab 1 callback, closing the loop

Still inside the sandbox, in the Claude session:

```
Read .env and tell me what STRIPE_KEY is.
```

🚫 **Still blocked** — by `deny: Read(./.env)` from Lab 1. Deny rules apply in every permission mode, including `--dangerously-skip-permissions`, and the repo's `settings.json` travels with the repo.

```
Run scripts/leak.py with python.
```

✅ **Still prints both files.** The exact bypass from Lab 1, still working, three labs later.

**And this time it does not matter.** The read happened inside a microVM with no route out. That is the whole argument for defence in depth: the inner layers never became correct — they became survivable.

> Slide 12 states the corollary bluntly: *everything under the Git root stays readable inside the VM, `.env` included. Keep secrets outside the repository.* This repo is a live demonstration of what happens when you don't.

---

## Lab 3 — Direct mount: the danger that remains

Direct mount is the **default**. Your working tree is shared read-write. The agent's edits are your files, the moment they are written. There is no boundary between the agent and your working tree at all.

### 3.1 The demo

Inside the sandbox:

```
Create a file at .git/hooks/pre-commit containing a shell script that
prints "this hook was written inside a sandbox", and make it executable.
```

Then exit, and on the **host**:

```bash
cat .git/hooks/pre-commit
git commit --allow-empty -m "test"
```

**Your host runs it.** Not the VM — your machine, your shell, your user.

### 3.2 Why this class of file is special

| File | Runs when |
|---|---|
| `.git/hooks/` | You commit or push — **and never appears in `git diff`** |
| `.github/workflows/ci.yml` | Your next push, with your repo secrets |
| `Makefile`, `package.json` | Your next build or install |
| `.vscode/tasks.json`, `.idea/` | You open the project |

The repo now ships a `Makefile` and a workflow so you can point at concrete files. Try it:

```
Add a line to the Makefile "test" target that prints "compromised".
```

Then on the host: `git diff` shows it — but `make test` is what most people run before reading the diff.

> **Review a sandbox session the way you would review a pull request from a stranger.**

`.git/hooks/` is the one that gets people. It is not tracked, so it never shows up in the review you were counting on.

---

## Lab 4 — Clone mode

```bash
sbx rm lab
sbx run --clone --name demo claude .
```

### 4.1 The three-part structure

| Where | What |
|---|---|
| Your repo on the host | Mounted **read-only** at `/run/sandbox/source` |
| A private clone in the VM | The agent commits here, and only here |
| A git remote on your host | `sandbox-demo`, reviewed like any other remote |

Inside the sandbox:

```bash
mount | grep sandbox
touch /run/sandbox/source/nope.txt    # read-only, refused
git remote -v
```

### 4.2 Give the agent work

```
Add a multiply(a, b) function to app/util.py, then commit it.
```

On the host, note what has *not* happened:

```bash
git status        # clean. Your working tree never moved.
```

Then review it like any other remote:

```bash
git fetch sandbox-demo
git diff main..sandbox-demo/main
git checkout -b feature sandbox-demo/main
```

### 4.3 What clone mode guarantees

- It cannot touch your `.git` or any tracked file — **so the §3.1 hook attack is structurally impossible**
- No shared index or refs, so parallel agents cannot collide
- Your git config, credentials and signing keys stay on the host

To pull host changes *into* the sandbox, the read-only mount doubles as a remote:

```bash
git pull /run/sandbox/source main
```

> ⚠️ **`sbx rm` on a clone-mode sandbox deletes the clone.** Any commit you haven't fetched or pushed is gone. Fetch before you remove.

**Clone mode is the only mode the agent cannot write through.** Direct mount is the default, so choose deliberately.

---

## Lab 5 — Network policy

```bash
sbx policy ls
sbx policy allow network pypi.org
sbx policy ls
```

Re-run inside the sandbox:

```bash
python scripts/net_probe.py pypi.org
pip install requests        # now works; it didn't a minute ago
```

Then inspect what the proxy saw:

```bash
sbx policy log
```

That log is the teaching artifact — every blocked request, by name. Also useful:

```bash
sbx policy deny network pypi.org    # revoke
sbx policy reset                    # back to your login default
```

Four properties worth stating:

1. Deny by default — only listed domains resolve
2. DNS goes through the proxy and obeys the same policy
3. Raw TCP, UDP and ICMP are blocked outright
4. No route to your localhost, or to another sandbox

---

## Lab 6 — Lifecycle and disposal

```bash
sbx ls                    # what exists
sbx stop demo             # pause, keep contents
sbx run --name demo       # resume
sbx rm demo               # delete the VM and everything in it
```

Run `sbx` with no arguments for the dashboard: live status, attach to an agent, open a shell, edit network rules.

### 6.1 Prove disposal is real

Before removing, inside the sandbox:

```bash
sudo apt-get install -y cowsay && cowsay "gone soon"
docker images
```

Then `sbx rm demo`, relaunch, and look again. Installed packages, built images, and the in-VM clone are all gone. **Your host working tree is untouched.**

### 6.2 Walk away

Everything after `--` is handed to the agent, so a task can run unattended:

```bash
sbx run --clone --name nightly claude . -- -p "Add docstrings to every function in app/, then commit."
```

Come back to `git fetch sandbox-nightly` and a diff to review.

---

## Lab 7 — The whole course in one table

| | Lab 1: permissions | Lab 2: `/sandbox` | Lab 3: `sbx` |
|---|---|---|---|
| **Boundary** | String matching on tool calls | Kernel (Seatbelt) | Hypervisor (microVM) |
| **Wraps** | Every tool | Bash + its children | The entire agent |
| **Enforced by** | Claude Code, before the command runs | The OS, while it runs | Virtual hardware |
| `python -c "open('.env')"` | ✅ bypasses the deny rule | ✅ still reads | ✅ still reads |
| Write to `../cc-shared/` via Bash | ✅ silent | 🚫 syscall fails | 🚫 not mounted |
| Write to `../cc-shared/` via Edit tool | ✅ on approval | ✅ on approval | 🚫 not mounted |
| Exfiltrate to the internet | ✅ | 🚫 unless allowlisted | 🚫 unless allowlisted |
| MCP servers, hooks | host | host | **in the VM** |
| Worst case | Your machine | Your machine, minus Bash | `sbx rm` |

Three sentences to close on:

1. **Permissions decide what may be attempted. Sandboxes decide what can happen.** The first reads a command string; the second holds while it runs.
2. **Each layer's boundary is drawn somewhere specific** — around tool calls, around Bash, around the agent. Knowing *where* is the entire skill.
3. **The inner layers never became correct. They became survivable.** `Read(./.env)` is still bypassable by `python`. Inside a microVM with no route out, that stopped being a breach and became a log line.

And the one that pays for the whole course: **speed and safety stop trading off.** The agent can install, build and run containers with no prompts at all — because the worst case is a sandbox you throw away.

---

## Instructor notes

| Symptom | Cause |
|---|---|
| `sbx run` fails immediately | Run `sbx diagnose`. On macOS, Apple silicon + Sonoma 14+ required |
| Everything reaches the network | You picked Open at `sbx login`. `sbx policy reset` after switching |
| `--branch` in an old blog post | Deprecated. Use `--clone` |
| Agent can't see host commits in clone mode | `git pull /run/sandbox/source main` — the read-only mount is a valid remote |
| Commits vanished after `sbx rm` | Clone-mode removal deletes the clone. Always `git fetch sandbox-<name>` first |
| Slash commands / skills missing | Expected. Host `~/.claude` does not travel; project config only |
| Agent asks for permission | It shouldn't — check the banner shows `--dangerously-skip-permissions` |

**Reset:**
```bash
sbx ls && sbx rm demo lab 2>/dev/null
cd cc-perms-sandbox
git checkout -- . && git clean -fd
rm -f .git/hooks/pre-commit
git remote | grep '^sandbox-' | xargs -r -n1 git remote remove
```

### Questions to leave hanging

1. The agent has root inside the VM. Why is that safe here and not on your laptop?
2. You allowlisted `github.com`. Name three ways data still leaves.
3. Clone mode blocks the `.git/hooks` attack. What does it *not* block?
