# Claude Code Permissions & Sandboxing — Teaching Labs

A single repo for three hands-on labs on where the boundary sits when you hand a coding agent your shell.

**Nothing in this repo is real.** `.env` and `secrets/api-keys.txt` contain training placeholders. `LAB_TOKEN` is fake. Every "credential" here exists to be harmlessly leaked in front of a class.

---

## The three labs

| Lab | Boundary | Enforced by | Guide |
|---|---|---|---|
| **1 — Permissions** | String matching on tool calls | Claude Code, before a command runs | [`docs/LAB1-PERMISSIONS.md`](docs/LAB1-PERMISSIONS.md) |
| **2 — `/sandbox`** | Kernel, around **Bash only** | Seatbelt / bubblewrap, while it runs | [`docs/LAB2-CLAUDE-SANDBOX.md`](docs/LAB2-CLAUDE-SANDBOX.md) |
| **3 — `sbx`** | Hypervisor, around **the whole agent** | A microVM | [`docs/LAB3-SBX.md`](docs/LAB3-SBX.md) |

They are designed to run in order. Each one breaks the previous one's boundary and asks what would have held.

### The spine

One directory, `../cc-shared/`, is the target in all three labs. The same one-line command behaves differently each time:

```bash
python -c "open('../cc-shared/style-guide.md','a').write('x')"
```

| Lab | Result |
|---|---|
| 1 | Runs silently. No prompt. The file changes. |
| 2 | Fails at the syscall — but Claude's `Edit` tool still writes there. |
| 3 | The directory does not exist. |

---

## Setup

```bash
git clone https://github.com/arifpucit/cc-perms-sandbox.git
cd cc-perms-sandbox
./setup.sh
claude
```

**Accept the workspace trust dialog.** Project `allow` rules grant capability, so Claude Code ignores them until you do. Skip it and you get a confusing half-broken lab where every `deny` fires and no `allow` does.

`setup.sh` creates:

- `../cc-shared/` — outside the repo and outside the working directory
- `~/.lab-secrets/fake_id_rsa` — a decoy credential, so Lab 2 never points at a student's real `~/.ssh`
- a `main` branch, which Lab 3's `sbx --clone` requires

Reset between sessions with `./reset.sh`.

### Requirements

| Lab | Needs |
|---|---|
| 1 | Claude Code |
| 2 | macOS (Seatbelt, nothing to install) or Linux/WSL2 with `bubblewrap` + `socat` |
| 3 | `sbx` — macOS Sonoma 14+ Apple silicon, Win 11 + Hypervisor Platform, or Ubuntu 24.04+ with KVM |

---

## Layout

```
<clone parent>/
├── cc-perms-sandbox/           ← git root == working directory == project root
│   ├── .claude/
│   │   ├── settings.json           team-shared rules  (committed)
│   │   ├── settings.local.json     personal overrides (committed HERE on purpose)
│   │   └── statusline.sh           shows the active model, for the Lab 1 precedence demo
│   ├── app/                        allowed to edit         → Edit(app/**)
│   ├── scripts/                    gated behind ask        → Edit(scripts/**)
│   │   ├── leak.py                 reads .env past the deny rule
│   │   ├── fs_probe.py             filesystem write/read table
│   │   ├── exfil.py                reads secrets, then actually attempts egress
│   │   ├── spawn.py                child + grandchild escape attempts
│   │   └── net_probe.py            DNS, raw TCP, ICMP, route back to host
│   ├── secrets/                    denied                  → Read(./secrets/**)
│   ├── sandbox-configs/            staged drop-in settings.local.json files for Lab 2
│   ├── docs/                       the three lab guides
│   ├── .env                        denied                  → Read(./.env)
│   ├── Dockerfile                  Lab 3: the sandbox's own Docker daemon
│   ├── Makefile                    Lab 3: a "runs later on your machine" file
│   └── .github/workflows/ci.yml    Lab 3: a "runs on your next push" file
└── cc-shared/                  ← created by setup.sh, outside everything
    └── style-guide.md
```

**The repo root is the project.** There is no `project/` subdirectory. Claude Code reads `.claude/settings.local.json` from the git repository root, so collapsing repo root, working directory, and project root into one path removes an ambiguity that would otherwise make Lab 1's precedence demo unreliable and Lab 3's `sbx` workspace confusing.

---

## Notes for instructors

`.claude/settings.local.json` is **committed** here, which is not what you would do in a real project. Lab 1 needs both settings files present on a fresh clone to teach precedence. Two consequences worth mentioning to students:

- Because the repository supplies the file, its `allow` rules go through the workspace trust check, exactly like `settings.json`.
- `/sandbox` writes your chosen mode into it, so `git status` will show changes mid-lecture. `.gitignore` has a commented-out line to switch this off once Lab 1 is done.

The two settings files deliberately disagree on `model`, `effortLevel`, and `defaultMode`. That conflict is the entire proof in Lab 1 §2 — do not "fix" it.

`.github/workflows/ci.yml` really does run on push. That is the point of the Lab 3 §3.2 demo, and it costs about ten seconds.
