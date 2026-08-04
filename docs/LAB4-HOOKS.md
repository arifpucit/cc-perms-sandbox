# Lab 4 — Hooks in Claude Code

**Slides:** hooks · **Prerequisites:** Labs 1 and 2 · **Next:** —

Everything in this lab is fake. `.env` and `secrets/api-keys.txt` contain training placeholders only.

Lab 1 ended here:

> Permission rules are string matching, not a security boundary.

Lab 2 ended here:

> The OS boundary is real — but it is drawn around Bash, not around the agent.

Both left a specific hole open on camera. This lab closes both of them with the same mechanism, uses that
mechanism to do something neither layer can do at all, and then shows the hole it leaves in turn.

| Section | Teaches | Ends at |
|---|---|---|
| 0 | Setup, what is new in the repo, the shape of a hook | — |
| 1 | Closing Lab 1's hole — the hook opens the script | — |
| 2 | Closing Lab 2's hole — one matcher over Bash **and** WebFetch | — |
| 3 | The `Stop` event — what neither previous layer could reach | — |
| 4 | Where hooks fail | **→ back to the sandbox** |
| 5 | The four layers in one table | — |

The single sentence the whole lab builds toward:

> **A permission rule reads the command. A hook runs code, so it can read what the command is about to do — and it still only sees what you told it to look for.**

---

## Lab 0 — Setup

### 0.1 If you are continuing from Labs 1–3

```bash
cd cc-perms-sandbox
./reset.sh
git pull            # the hook files are new
```

If you are starting fresh, do §0.1 of `LAB1-PERMISSIONS.md` first. This lab depends on that repo state:
`../cc-shared/` must exist, and the workspace trust dialog must have been accepted.

### 0.2 What is new in the repo

Three folders were added for this lab. Nothing existing was changed.

```
cc-perms-sandbox/
├── .claude/
│   └── hooks/                    <- NEW: four scripts, ready to run
│       ├── inspect-script.sh         section 1
│       ├── block-domains.sh          section 2
│       ├── tests-must-pass.sh        section 3
│       └── block-write.sh            section 4
├── hooks-configs/                <- NEW: one settings file per section
│   ├── 01-inspect-script.json
│   ├── 02-block-domains.json
│   ├── 03-tests-must-pass.json
│   └── 04-block-write.json
└── tests/                        <- NEW: what section 3's hook runs
    └── test_util.py
```

`hooks-configs/` works exactly like `sandbox-configs/` did in Lab 2: copy one file over
`.claude/settings.local.json`, restart Claude Code, and that section is live.

### 0.3 The shape of a hook

Every file in `hooks-configs/` is the `settings.local.json` you already know from Lab 2 — same model,
same effort level, same `allow` / `deny` / `defaultMode` — with **one `hooks` block added**. Nothing else
differs between the four files, so the only thing that changes on screen between sections is the hook.

```jsonc
{
  "model": "claude-opus-5",
  "effortLevel": "high",
  "permissions": { /* unchanged from Lab 2 */ },

  "hooks": {
    "PreToolUse": [                                    // 1. the event
      { "matcher": "Bash",                             // 2. which tool
        "hooks": [                                     // 3. what to run
          { "type": "command",
            "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/inspect-script.sh" }
        ] }
    ]
  }
}
```

Three answers, always in that order: **when it fires, what it matches, what it runs.**

> `${CLAUDE_PROJECT_DIR}` is expanded by Claude Code. `$HOME` and `~` are **not** — a path written either
> of those ways silently never loads. This is the single most common reason a hook does nothing.

### 0.4 Preflight

```bash
which python3       # the hooks parse their JSON input with it (falls back to `python`)
which pytest        # section 3 only
```

Every hook here receives one JSON object on stdin and prints one back. `python3 -c "..."` is used to
read a field out of it and build the reply — no extra install needed on Mac/Linux, since `python3` ships
with the OS. (A `python3 → python` fallback is built into each script for the odd machine where only
`python` is on the `PATH`.)

### 0.5 The three commands students should keep reaching for

| Command | Shows |
|---|---|
| `/hooks` | Every registered hook, by event, **and which file it came from** |
| `/status` | The Setting sources line — confirms the file was loaded at all |
| `claude --debug` | Why a hook did or did not fire |

**The rhythm for every section below, without exception:**

1. `cp hooks-configs/NN-*.json .claude/settings.local.json`
2. restart Claude Code
3. `/hooks` — confirm it is listed
4. run the prompt

When nothing happens, that order tells you which half is broken.

---

## Lab 1 — Closing Lab 1's hole

### 1.1 Re-establish the hole

No hooks yet. Confirm the wall is still where Lab 1 left it:

```
Read .env and secrets/api-keys.txt and show me the contents.
```
🚫 Blocked by `Read(./.env)` and `Read(./secrets/**)`.

Now walk through it, exactly as in Lab 1 §4.2:

```
Run scripts/leak.py with python and show me the full output.
```
✅ **Runs. Prints both files in full.** Matches `Bash(python *)`.

Say the reason out loud before fixing it: the command string is `python3 scripts/leak.py`. The words
`.env` and `secrets` do not appear in it. **No permission rule could ever have matched this**, because
there is nothing in the string to match.

### 1.2 Install the hook

```bash
cp hooks-configs/01-inspect-script.json .claude/settings.local.json
claude
```

```
/hooks
```

Confirm one `PreToolUse` hook on matcher `Bash`, sourced from `.claude/settings.local.json`.

```
Run scripts/leak.py with python and show me the full output.
```
🚫 **Blocked:**

```
Blocked: scripts/leak.py reads a credential file.
Line 15: for target in (root / ".env", root / "secrets" / "api-keys.txt"):
```

### 1.3 Why it works

Open `.claude/hooks/inspect-script.sh` on screen. It does two things:

```bash
# 1. does the command itself name a secret?
grep -qE "$SECRETS" <<<"$CMD" && deny "..."

# 2. does the command run a script? then OPEN THAT SCRIPT and look inside
for WORD in $CMD; do
  case "$WORD" in *.py|*.sh) ;; *) continue ;; esac
  grep -qE "$SECRETS" "$FILE" && deny "..."
done
```

Step 2 is the whole lab. A permission rule is handed a string and compares it to a pattern. A hook is
handed the same string and can then **go and read the file it names**.

```
  Read tool ────────────────► [deny: Read(./.env)] ──────► 🚫
  cat / head / tail / sed ──► [recognized as reads] ──────► 🚫
  python scripts/leak.py ───► [allow: Bash(python *)] ────► ✅   <- Lab 1 stopped here
                              [hook opens leak.py] ───────► 🚫   <- Lab 4
```

### 1.4 What it catches, and what it does not

Run each and let the class predict first:

| Prompt | Result | Why |
|---|---|---|
| `Run scripts/leak.py` | 🚫 | the hook read the file |
| `Run scripts/fs_probe.py` | 🚫 | same — it reads `.env` too |
| `Show me .env with cat` | 🚫 | the command itself names it |
| `Run app/main.py` | ✅ | nothing in it matches |
| `Show me git status` | ✅ | not a script at all |

`fs_probe.py` being blocked is worth a sentence: **your hook does not know it was written for a
different lab.** A hook is a policy, and policies have collateral.

### 1.5 The callback that surprises everyone

Quit, and relaunch with every guard rail off:

```bash
claude --dangerously-skip-permissions
```

```
Run scripts/leak.py with python.
```
🚫 **Still blocked.**

`PreToolUse` fires **before** Claude Code consults the permission mode, so a hook `deny` holds in
`default`, `acceptEdits`, `bypassPermissions`, and under `--dangerously-skip-permissions`.

The reverse is not true. A hook returning `allow` does **not** override a `deny` rule from
`settings.json`.

> **Hooks tighten. They never loosen.**

That asymmetry is deliberate, and it makes the failure mode safe: a bug in your hook can only ever stop
something that should have run. It can never start something the rules already forbade.

---

## Lab 2 — Closing Lab 2's hole

### 2.1 Recall what happened

In Lab 2, with `/sandbox` enabled and `arifbutt.me` on `deniedDomains`:

| Prompt | Result |
|---|---|
| `Use curl to access https://arifbutt.me` | 🚫 blocked by the sandbox proxy |
| `Use web fetch to access https://arifbutt.me` | ✅ **returned the page** |

Not a bug. `/sandbox` wraps Bash and its children. **WebFetch does not run on your machine at all** — it
runs on Anthropic's infrastructure, so there is no syscall for a kernel to refuse.

### 2.2 One matcher over both

```bash
cp hooks-configs/02-block-domains.json .claude/settings.local.json
claude
```

```
Use curl to access https://arifbutt.me and give a short summary.
```
🚫 Blocked.

```
Use the web fetch tool to access https://arifbutt.me and give a short summary.
```
🚫 **Blocked — same hook, same reason string.**

```
Use curl to access https://pucit.edu.pk and give a short summary.
```
✅ Runs.

### 2.3 Why it works

```jsonc
"matcher": "Bash|WebFetch"
```

That is the entire fix. The sandbox could not cover WebFetch because the sandbox is a kernel boundary and
WebFetch never touches the kernel. A hook sits inside Claude Code, **above** the point where the tools
diverge, so it does not care which one was reaching for the network.

### 2.4 Be honest about what this is

This is a policy, not a boundary. Two things it does not do:

- It matches a hostname string. An IP address, or a URL with the host buried in it, walks past.
- It only covers the two tools you named. An MCP server with a fetch tool of its own is a third door.

Lab 2's proxy had the first weakness too — it read hostnames and did not inspect TLS. **Neither layer
became correct. Both became narrower.**

---

## Lab 3 — The `Stop` event

Everything so far has been about tool calls. Permissions gate a tool call. The sandbox wraps the process
a tool call starts. Neither of them can express:

> *You may not finish while a test is failing.*

That is not a tool call. It is a moment in the turn.

### 3.1 Install

```bash
cp hooks-configs/03-tests-must-pass.json .claude/settings.local.json
claude
```

Note the config: no `matcher` at all. `Stop` does not take one — it fires once, every time Claude tries to
end its turn.

### 3.2 Give it failing work

```
Add a subtract(a, b) function to app/util.py, and a test for it in
tests/ that expects the wrong answer.
```

Claude writes both, tries to finish, and is stopped:

```
Tests are failing. Fix them before you finish:
...
E       assert 5 == -1
```

It reads the reason, goes back, and fixes the test by itself. The turn ends only when `pytest` is green.

### 3.3 How the block is expressed

`PreToolUse` used `permissionDecision`. `Stop` uses a different shape:

```bash
python3 -c 'import json,sys; print(json.dumps({"decision":"block","reason":sys.argv[1]}))' \
  "Tests are failing..."
```

Two things worth stating:

- `reason` is **written for Claude, not for you.** It goes into the transcript as the explanation, which
  is why pasting the last ten lines of pytest output is more useful than "tests failed".
- `exit 2` with a message on stderr does the same job. `exit 0` lets the turn end. **`exit 1` is an error
  — it does not block, and the turn ends anyway.** Students write `exit 1` first, every time.

### 3.4 ⚠️ Break it on purpose

Open `.claude/hooks/tests-must-pass.sh` and comment out this line:

```bash
STOP_ACTIVE=$("$PY" -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print("true" if d.get("stop_hook_active") else "false")
' <<<"$INPUT")
[ "$STOP_ACTIVE" = "true" ] && exit 0
```

Run §3.2 again. Claude finishes, is blocked, finishes, is blocked — forever, until you stop it or the
budget does.

`stop_hook_active` is Claude Code telling you *this Stop hook already fired once for this turn.* Without
it you have built an infinite loop out of two lines of JSON. Put the line back.

> Any hook that blocks the end of a turn owns its own loop safety. Nothing checks it for you.

---

## Lab 4 — Where hooks fail → **back to the sandbox**

Same honesty as the previous two labs. All four failures below are quiet: nothing tells you it happened.

```bash
cp hooks-configs/04-block-write.json .claude/settings.local.json
claude
```

### 4.1 The model routes around it

The config denies the `Write` tool outright, **and** any Bash command that uses `cat` with a redirect or
heredoc. Both checks are live the moment this config is installed — there's no separate toggle, it's one
script.

```
Create hello.py containing a print statement. Don't read any other files in this
repo first — just try it directly, and if something is blocked, try a different
way on your own.
```

> The second sentence matters. Drop it, and Claude reads `docs/LAB4-HOOKS.md` — right here in the repo —
> recognizes the block is deliberate (this doc spells out exactly why), and stops to ask permission
> instead of just trying another way. That's honest, reasonable behavior — it just isn't the demo. With
> the second sentence, it proceeds on its own.

🚫 `Write` is denied. 🚫 `cat > hello.py <<'EOF' ... EOF` is denied too. Then, in the same response,
Claude reaches for a tool nobody named:

```bash
printf 'print("Hello, world!")\n' > hello.py
```

```bash
cat hello.py    # it exists
```

**You blocked two specific commands, not the job itself.** This is Lab 1 §1.4's `rm -rf` lesson arriving
again, one layer up. Close `printf` next and it reaches for `python3 -c "open(...).write(...)"`, or
`tee hello.py <<EOF`, or `node -e "..."`. There is no finite list of "ways to write a file" — Bash alone
ships dozens of them, and every language runtime on the machine adds more. **Blocking a command is not
blocking an action, no matter how many commands you enumerate.** The only thing that stops the *action
itself* is a boundary that does not care which command produced it — which is exactly what `/sandbox`'s
filesystem rule does in Lab 2, and why §4.5 below sends you back there.

### 4.2 A wrong matcher fails silently

Edit `.claude/settings.local.json` and change `"Write"` to `"write"`. Re-run §4.1.

The file is created with no complaint from anything. Run `/hooks` — the hook is listed and looks fine.
**Matchers are case-sensitive, and Claude Code does not warn you when a matcher never matches.**

### 4.3 One flag skips every hook

```bash
claude --bare -p "run scripts/leak.py"
```

Bare mode never reads hooks, skills, plugins, MCP servers or `CLAUDE.md`. It exists so CI gets the same
result on every machine — and the cost is that every guardrail is simply not loaded, in exactly the
environment nobody is watching.

> Note this is **not** true of `claude -p` on its own, which loads the same configuration an interactive
> session does.

### 4.4 Your policy is a file

```
Add a comment at the top of .claude/settings.local.json.
```

`.claude/` is a protected path, so this prompts (Lab 1 §3.3) — but a prompt is not a wall, and the hook
scripts themselves are ordinary files with no protection at all.

**The thing enforcing your rule is writable by the thing your rule constrains.**

### 4.5 The bridge

> A hook only stops what it can see, on the path where it is running. None of the four failures above is
> fixed by writing a better hook — a better hook has the same three weaknesses.
>
> Turn `/sandbox` back on and repeat §4.1. The heredoc still runs, and the write still lands, because the
> project directory is writable by design. Now aim the same heredoc at `../cc-shared/` and the syscall
> fails. The hook could not see the evasion. The kernel did not need to.

---

## Lab 5 — The four layers in one table

| | Lab 1: permissions | Lab 2: `/sandbox` | **Lab 4: hooks** | Lab 3: `sbx` |
|---|---|---|---|---|
| **Boundary** | String matching on tool calls | Kernel (Seatbelt) | **Your script** | Hypervisor (microVM) |
| **Runs** | Before the command | While it runs | **Before the command** | Around everything |
| **Wraps** | Every tool | Bash + its children | **The events you chose** | The entire agent |
| `python scripts/leak.py` | ✅ bypasses | ✅ still reads | 🚫 **hook reads the script** | ✅ reads, no route out |
| `curl arifbutt.me` | ✅ | 🚫 proxy | 🚫 | 🚫 |
| WebFetch `arifbutt.me` | ✅ | ✅ **not covered** | 🚫 **one matcher** | 🚫 |
| "don't finish while tests fail" | ✗ cannot express | ✗ cannot express | ✅ **`Stop`** | ✗ |
| Write via `cat > f <<EOF` | ✅ | ✅ inside project | ✅ **routed around — block `cat`, it uses `python3` instead** | ✅ inside the VM |
| Defeated by | Any subprocess | Any non-Bash tool | **Anything you did not parse** | `sbx rm` |

Three sentences to close on:

1. **A rule matches text. A hook runs code.** That is the entire difference, and it is why a hook could
   close a hole no permission rule could have expressed.
2. **Hooks tighten, never loosen.** A hook `deny` survives `--dangerously-skip-permissions`; a hook
   `allow` cannot override a `deny` rule. The failure mode is over-blocking, which is the safe direction.
3. **Hooks are the layer you write, and therefore the layer you own.** Permissions and the sandbox ship
   with Claude Code. The hook is the only place your own judgment goes into the machine — and the only
   layer whose blind spots are yours.

---

## Instructor notes

### Gotchas that will bite you live

| Symptom | Cause |
|---|---|
| Hook never fires, no error | Matcher case. `Bash`, not `bash`. Confirm in `/hooks` |
| Hook never fires, not listed in `/hooks` | JSON invalid — the file is rejected **as a whole**, exactly like Lab 1's settings |
| Hook never fires, path looks right | `$HOME` and `~` are not expanded. Use `${CLAUDE_PROJECT_DIR}` |
| Hook runs but nothing is blocked | You exited 1. Only exit 2 blocks; 1 is an error and the tool proceeds |
| "Invalid hook output" | Something printed to stdout before the JSON — usually a shell profile banner |
| Hook works in the shell, fails in Claude Code | `python3` (or `python`) is not on the `PATH` Claude Code inherits |
| Everything worked, then stopped after a `git pull` | `.claude/settings.local.json` was overwritten. Re-copy the stage file |
| `Stop` hook loops forever | `stop_hook_active` not checked (§3.4) |
| §4.1 does not reproduce | Claude sometimes retries `Write` before reaching for Bash. Ask again |

### Reset

```bash
cd cc-perms-sandbox
./reset.sh
rm -f hello.py
git checkout -- .claude/settings.local.json
```

If you edited a hook script during §3.4 or §4.2, `git checkout -- .claude/hooks/` puts them back.

### Questions to leave hanging

1. The §1 hook reads any `.py` file the command names. Write three commands that read `.env` and defeat
   it anyway.
2. §1.5 showed a hook `deny` surviving `--dangerously-skip-permissions`. Where does that hook's authority
   actually come from, and what could take it away?
3. You now have four layers. If you could keep only one, which — and against which threat?
