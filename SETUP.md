# SETUP.md — the paranoid install guide

If you can `make setup && make verify` green in under 30 minutes, skim this
document. If anything goes wrong, come back here and read the relevant
section end to end. Every anticipated trap in this file is based on a real
student complaint from a prior cohort.

**Rule of thumb: if a step's output doesn't match what this doc shows, STOP
and fix before moving on. Compounding setup errors is how people lose a
weekend.**

---

## 1. Prerequisites

You need:

- **Python 3.12.x** (exactly 3.12 — not 3.11, not 3.13). `uv` can install it for you.
- **Git** (any recent version)
- **`uv`** (the Python package manager; we prefer it over pip)
- **Make** (already present on macOS/Linux; on Windows, use WSL — see §Windows below)
- **For Ex6:** Docker (24.0 or newer). Ex5/7/8 do not need Docker.
- **For Ex8 voice mode:** working audio on your machine (microphone + speakers).
  Ex8 works fine in text-only mode without audio.

Check what you have:

```
python --version          # should print "Python 3.12.x"
git --version
uv --version              # if this fails, see §Install uv below
make --version
docker --version          # only needed for Ex6
```

### Platform-specific quirks (read the one you're on)

- **macOS** → `docs/setup-macos.md` (Homebrew quirks, Apple Silicon notes)
- **Linux** → `docs/setup-linux.md` (Debian/Ubuntu/Fedora traps)
- **Windows** → `docs/setup-windows.md` (**we strongly recommend WSL**;
  native Windows works for some but not all of Ex8)

---

## 2. Clone the repo

```
git clone https://github.com/sovereignagents/homework-pub-booking.git
cd homework-pub-booking
```

**Anticipated traps:**

- **Clone path has spaces**: `~/My Projects/homework-pub-booking` breaks some
  tools. Use `~/code/homework-pub-booking` or similar.
- **Clone is inside OneDrive / iCloud / Dropbox**: the syncer will race with
  Rasa's model builds and cause intermittent corruption. Clone into a local
  directory OUTSIDE your cloud sync.
- **Windows native path with forward slashes**: if you're on native Windows,
  clone into your WSL home, not your Windows user folder.

---

## 3. Install uv

`uv` is a fast Python package manager — 10-100x faster than pip, handles
Python versioning, and what sovereign-agent uses internally. We use it here
for consistency.

**Three ways to install it**, pick whichever you trust:

1. The official installer (recommended by Astral):
   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. With Homebrew on macOS:
   ```
   brew install uv
   ```
3. With pip:
   ```
   python -m pip install uv
   ```

**Anticipated traps:**

- `curl | sh` warnings from your security team: options 2 or 3 produce the
  same binary without the pipe.
- `uv: command not found` after install: `uv` is installed but not on PATH.
  On macOS/Linux, open a new shell or `source ~/.bashrc` (or `~/.zshrc`).
  On Windows WSL, `source ~/.bashrc`.

Confirm:

```
uv --version
```

Expected output: `uv X.Y.Z` (any recent version ≥ 0.5).

---

## 4. Run `make setup`

```
make setup
```

What it does, step by step:

1. Installs Python 3.12 via uv (if your system doesn't have it already).
2. Creates `.venv/` in the repo root.
3. Installs `sovereign-agent == 0.2.0` and all dependencies (including dev
   tools: pytest, ruff).
4. Creates `.env` from `.env.example` if not present. You still need to
   fill in `NEBIUS_KEY`.

Expected output (approximate):

```
Resolved 48 packages in 120ms
Downloading packages... ✓
Installed 48 packages in 8.2s
✓ Created .env from template. Edit it and set NEBIUS_KEY.
✓ make setup done. Next: edit .env, then run 'make verify'.
```

**Anticipated traps:**

- **Network error during pip resolution**: retry with `make clean-all && make setup`. A
  corporate proxy may be the culprit; set `PIP_INDEX_URL` in your shell.
- **Permission denied in .venv**: you ran `uv` under `sudo` previously. Fix with:
  `rm -rf .venv && make setup` (without sudo).
- **SSL certificate error on corporate network**: see `docs/troubleshooting.md`
  entry "SSL errors on corporate networks".
- **"No matching distribution found for sovereign-agent == 0.2.0"**: you may be
  running `make setup` BEFORE `sovereign-agent 0.2.0` has been published to
  pypi. Check with `pip index versions sovereign-agent`. If the cohort hasn't
  formally started yet, wait for the announcement.

---

## 5. Get your Nebius API key

**You need this before `make verify` will pass.**

Step-by-step with screenshots: `docs/nebius-signup.md`.

TL;DR: go to https://tokenfactory.nebius.com, sign up with your GitHub account,
go to "API Keys" → "Create", copy the string that starts with `eyJ...`. Free
tier is more than enough for every exercise many times over.

**Anticipated traps:**

- Signing up with your personal email instead of the one your cohort is
  registered under: free-tier limits are per-account. If your cohort
  provides credits, they go to the specified email.
- Confusing the model-studio key with the token-factory key: the homework
  uses Token Factory. The UI is at https://tokenfactory.nebius.com, NOT
  `studio.nebius.ai`.

---

## 6. Configure your `.env`

**Read `docs/dotenv-101.md` end-to-end if you've never used `.env` before.**
It is NOT a shell script and WILL NOT export variables into shells you spawn.
You have been warned.

Specific to this project:

Open `.env` in your editor (created for you by `make setup`).

Replace only this line:

```
NEBIUS_KEY=
```

with:

```
NEBIUS_KEY=eyJhbGciOi...  # your actual Nebius key
```

Leave everything else alone. The defaults are what the grader uses.

Verify it's loaded:

```
make verify
```

Look for `NEBIUS_KEY loaded: yes` in the output.

**Anticipated traps:**

- `.env` vs `.env.local` vs `env.sh`: only `.env` is read here. There is no
  automatic chaining. If you want to keep local overrides out of git, put
  them in `.env` and trust `.gitignore`.
- Quoting: both `NEBIUS_KEY=abc123` and `NEBIUS_KEY="abc123"` work. **Smart
  quotes** from Notion/Word DO NOT work — they look like `"` but are actually
  different Unicode characters. If you copy-pasted, retype the quotes.
- Trailing whitespace: `NEBIUS_KEY=abc123   ` with trailing spaces is a
  different string than `NEBIUS_KEY=abc123`. Your editor may auto-strip on
  save; if not, trim manually.
- `export NEBIUS_KEY=...`: `.env` is not shell. The `export` keyword is
  ignored by `python-dotenv` but may confuse other tools. Omit it.

---

## 7. Run `make verify`

```
make verify
```

What it does:

1. **Preflight**: ruff check, pytest collection, sovereign-agent imports.
2. **Nebius smoke test**: makes ONE real LLM call (cost: <£0.001) to confirm
   your key works and the model endpoint is reachable.
3. **Ex5 offline dry-run**: imports your starter scaffold and runs it under
   `FakeLLMClient`. Confirms the sovereign-agent integration is wired up.

Expected final line:

```
✓  All checks passed — ready to start the homework!
```

**If you see `✗`:**

Each failure line points at a specific doc or troubleshooting entry. Read that
first, fix the issue, and re-run `make verify`. Loop until green.

If you can't get `make verify` green after 30 minutes of trying, paste the FULL
output (not a screenshot — the text) into `#module1-agents` or open a GitHub
issue with the `setup` label. Do not suffer in silence; getting unstuck is part
of the process.

---

## 8. (Optional) Install Docker + Rasa for Ex6

Ex6 uses Rasa as a structured-dialog backend. Rasa runs as a Docker container
so you don't have to fight Python version conflicts.

Detailed guide: `docs/rasa-docker.md`.

TL;DR:

1. Install Docker Desktop (macOS/Windows) or `docker` + `docker-compose` (Linux).
2. `docker pull rasa/rasa-pro:latest` (takes ~2 GB).
3. The first `make ex6-real` will spin up the container automatically.

**You can complete Ex5, Ex7, Ex8, and Ex9 without Docker.** Ex6 is the only one
that needs it.

---

## 9. (Optional) Install Speechmatics for voice in Ex8

Ex8 supports TWO modes:

- **Text mode** (default): simulates voice by using printed transcripts.
  No extra setup. Works for everyone.
- **Voice mode**: real STT via Speechmatics and real TTS via ElevenLabs.
  Requires two additional API keys.

Text-only mode is sufficient for full credit on most of Ex8. Voice mode is
a differentiator for students who want to stretch themselves.

Detailed guide: `docs/speechmatics-setup.md`.

---

## 10. What to do if you're stuck for > 30 minutes

1. **Run `make verify`** and paste the output. It diagnoses almost everything.
2. **Check `docs/troubleshooting.md`** — it's organised by error message, not
   by exercise.
3. **Search the #module1-agents channel** before posting. Someone may have
   asked yesterday.
4. **Post in #module1-agents** with:
   - The exact command you ran
   - The full error output (not a screenshot, the text)
   - Your OS and Python version
5. **Open a GitHub issue** with the `setup` label if the problem persists.

Getting unstuck is part of the course, not a failure. The goal is that you
learn, not that you prove you can install things alone.
