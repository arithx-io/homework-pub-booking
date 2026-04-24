# dotenv-101 — what a `.env` file is and how it gets loaded

If you've never used `.env` before (or have used it once and it Just Worked
without you knowing why), read this end-to-end. Most of the "my variable
isn't being picked up" support tickets come from the confusions below.

## The short version

A `.env` file is **not** a shell script. It is a plain text file of
`KEY=VALUE` lines that the Python package `python-dotenv` reads and
injects into `os.environ`. Other tools (12-factor-compliant ones) read
it similarly.

The homework's `make setup` creates `.env` from `.env.example`. You edit
it to add your real API key. `make verify` reads it before calling Nebius.

## The long version

### Location

`.env` lives at the ROOT of the homework repo — next to `pyproject.toml`,
not in any subdirectory. `python-dotenv` searches the current working
directory and its parents; the repo root is the expected location.

### Format

```
# Lines starting with # are comments.
# Blank lines are ignored.

KEY_1=value-no-quotes
KEY_2="value with spaces"
KEY_3='single quotes also fine'
KEY_4=value=with=equals=signs     # everything after the first = is the value

# NO export keyword:
export KEY_5=value                 # <- the `export` is IGNORED by python-dotenv but works in shells
```

Common mistakes:

- `KEY = value` (spaces around `=`) — some loaders treat this as
  `KEY ` (with trailing space) → different from `KEY`. Remove the spaces.
- `KEY=value   ` (trailing whitespace) — different string than `KEY=value`.
- `KEY="value"` and `KEY=value` — both work, but you CANNOT mix them in
  the same line (`KEY="value` breaks).
- Smart quotes (`"`, `"`, `'`, `'`) from Notion/Word — visually identical
  to regular quotes but different Unicode. Retype the quotes in a code editor.

### How Python loads it

In the homework, two paths load `.env`:

1. `sovereign-agent`'s `Config.from_env()` calls an internal
   `_load_dotenv()` when you import or run the framework.
2. Our `scripts/preflight.py` and `scripts/nebius_smoke.py` load it
   directly because they run BEFORE the framework imports.

Both do the same thing: read `KEY=VALUE` lines, set `os.environ[KEY] = VALUE`
if `KEY` is not already set in the shell environment. Important: **shell env
wins over .env**. If you have `NEBIUS_KEY=foo` exported in your shell and
`.env` says `NEBIUS_KEY=bar`, Python sees `foo`.

### What `.env` does NOT do

- It does NOT get loaded into your shell. `echo $NEBIUS_KEY` in your
  terminal will print empty even after editing `.env`.
- It does NOT export variables to subprocesses unless those subprocesses
  also read `.env`.
- It does NOT support variable substitution (`KEY_2=${KEY_1}_suffix`).
  python-dotenv has an option for this but we don't enable it.
- It does NOT override variables you've already set in the shell.

### When "the variable isn't being read"

Run this one-liner at the repo root:

```
uv run python -c "from dotenv import load_dotenv, dotenv_values; load_dotenv(); import os; print('shell:', os.environ.get('NEBIUS_KEY', '(unset)')); print('file:', dotenv_values('.env').get('NEBIUS_KEY', '(not in .env)'))"
```

This prints what the shell sees vs what the file has. The most common
diagnoses:

| Shell | File | Meaning |
|---|---|---|
| (unset) | (not in .env) | You haven't filled in .env. |
| (unset) | `eyJ...` (real key) | Good — Python will read from the file. |
| `your-nebius-key-here` | `eyJ...` | Shell has a stale value. Run `unset NEBIUS_KEY` and retry. |
| `eyJ...` (different key) | `eyJ...` | Both set, shell wins. Usually fine. |

### CRLF line endings (Windows)

Files edited in Notepad or other Windows editors may have `\r\n` line
endings. Most Python loaders handle this, but some tools (especially
Makefiles) do not. In VS Code, bottom-right corner says "CRLF" or "LF" —
click it and choose LF. Save the file.

### Committing .env

**Never.** `.env` contains secrets. The homework's `.gitignore` excludes
it. If you accidentally committed it, rotate the key (go to the Nebius
dashboard, revoke, create a new one) and:

```
git rm --cached .env
git commit -m "remove accidentally committed .env"
git push
```

The secret is in git history — even deleting from `.env` in a later
commit doesn't erase it. Rotation is mandatory.
