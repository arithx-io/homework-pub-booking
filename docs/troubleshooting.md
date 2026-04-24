# Troubleshooting — organised by error message

Students from prior cohorts have hit every one of these. If your symptom
matches an entry here, try the fix BEFORE asking for help — it'll save
you hours.

If your symptom isn't listed and it took you more than 30 minutes to
resolve, please open a PR adding it. The doc grows from real incidents.

---

## 1. `ModuleNotFoundError: No module named 'sovereign_agent'`

Your virtualenv isn't activated, or `make setup` didn't finish.

```
# Confirm the venv:
ls .venv/bin/python  # should exist
uv run python -c "import sovereign_agent"  # uv run = activated
```

If the import still fails, wipe and reinstall:

```
make clean-all
make setup
```

## 2. `NEBIUS_KEY not set`

Your `.env` file is missing, malformed, or you're running commands that
don't load it. See **docs/dotenv-101.md** for the full explanation.

Quick checks:

```
ls -la .env                    # file exists?
cat .env | grep NEBIUS_KEY     # value is set (non-empty, no quotes around NEBIUS_KEY=)?
make verify                    # re-run after editing
```

## 3. `rate limit exceeded` / `429` from Nebius

Nebius free tier has per-minute limits. The smoke test and `make ex*-real`
can hit them if you run them in quick succession.

**Fix:** wait 60 seconds and retry. If it persists, you may have exhausted
your monthly credit — check your dashboard at
[tokenfactory.nebius.com](https://tokenfactory.nebius.com).

Offline exercises (`make ex5`, not `make ex5-real`) don't burn tokens.

## 4. `docker: command not found`

Docker is not installed. You only need it for Ex6.

- **macOS/Windows:** install Docker Desktop from docker.com.
- **Linux:** `sudo apt install docker.io` (Debian/Ubuntu) or your
  distro's equivalent, then `sudo usermod -aG docker $USER` and re-login.

## 5. `docker daemon not running`

Docker is installed but the daemon isn't up.

- **macOS/Windows:** open Docker Desktop; wait for the whale icon to go steady.
- **Linux:** `sudo systemctl start docker`.

## 6. "Port already in use" (Rasa: 5005 or 5055)

Something else (or a stale Rasa from an earlier run) holds the port.

```
# Find what's using 5005:
lsof -i :5005                  # macOS/Linux
netstat -ano | findstr :5005   # Windows

# Kill the container:
docker ps | grep rasa
docker stop <container-id>
```

## 7. `rasa train` fails silently

Usually `domain.yml` or `flows.yml` has invalid YAML. Run with `--debug`:

```
docker run --rm -v $(pwd)/rasa_project:/app rasa/rasa-pro:latest train --debug
```

The last 20 lines name the offending file and column.

## 8. `complete_task not called` — the v0.1.0 failure 8 lesson

The framework expects agents to eventually call `complete_task` to mark
a session done. If your trace shows the executor hitting max_turns without
calling it, the LLM got stuck in a reasoning loop.

**Workaround:** in your scripted `FakeLLMClient` responses, always end with
a `complete_task` tool call. The reference `examples/pub_booking/run.py` in
sovereign-agent shows the pattern.

## 9. Session directory evaporates — can't inspect after a run

You're running examples that use `tempfile.TemporaryDirectory()`. By design,
the homework writes to `user_data_dir() / "homework" / exN` instead:

- Linux: `~/.local/share/sovereign-agent/homework/exN/`
- macOS: `~/Library/Application Support/sovereign-agent/homework/exN/`
- Windows: `%LOCALAPPDATA%\sovereign-agent\homework\exN\`

If you want a specific location, set `SOVEREIGN_AGENT_DATA_DIR` in `.env`.

## 10. "My review / flyer mentions the wrong functions" — v0.1.0 failure 6

LLMs (especially thinking models) occasionally mix up tool names or
fabricate parameter names. That's what the dataflow integrity check is for.

If the fabrication is in a CRITICAL field (venue name, price), your check
MUST catch it. If it's in a descriptive field ("serves wonderful fish"),
it's harmless.

## 11. `ruff check` fails in CI but passes locally

Version mismatch. Pin ruff by re-running `uv sync --all-groups` — the
lockfile has the CI version.

```
uv run ruff --version          # must match .github/workflows/ci.yml
```

## 12. Test failures on fast hardware (Apple Silicon, etc.)

The sovereign-agent test suite has a known ms-timing issue on fast machines
(see sovereign-agent's CHANGELOG). If a test is flaky because of "ran in
0ms, expected >=1ms", add a 2ms sleep to disambiguate.

Your homework tests should not have this problem — but if you see it,
report it in `#module1-agents`.

## 13. Windows path issues

**You are on native Windows without WSL.** Stop. Switch to WSL.

```
wsl --install -d Ubuntu-22.04
```

Then clone the repo inside WSL (in `~`, not on `/mnt/c/`). All our
test commands, Docker integrations, and voice setup assume a Unix
path model.

## 14. `uv: command not found` after installing it

`uv` is installed but not on PATH. Open a new shell, or:

```
# zsh users:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# bash users:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## 15. Speechmatics rate limited

Free tier of Speechmatics has a per-day audio-minutes cap. Text mode
of Ex8 does not use Speechmatics at all and can earn full credit.

Degrade: run `make ex8-text` instead of `make ex8-voice`.

## 16. `git push` fails with "Permission denied (publickey)"

You cloned the repo with SSH but your SSH key isn't added to GitHub.

Two options:

- Add your key: https://github.com/settings/keys
- Switch the remote to HTTPS:
  ```
  git remote set-url origin https://github.com/<you>/homework-pub-booking.git
  ```

## 17. `check-submit` says "0/100" with no details

The script crashed silently. Re-run with `--verbose`:

```
python -m grader.check_submit --verbose
```

The last stack trace before the "0/100" line tells you what blew up.

## 18. "sovereign-agent 0.2.1 available — should I upgrade?"

Read CHANGELOG-v2026.04.0.N first (if that file exists in the repo root).
If it says "required: yes", bump `pyproject.toml` to the new version and
re-run `uv sync`. If "required: no", you can stay on `0.2.0`; the grader
runs against the pinned version either way.

## 19. Apple Silicon arm64 vs x86 container (Rasa)

Rasa's official image is x86_64 by default. On M1/M2/M3:

```
docker pull --platform linux/amd64 rasa/rasa-pro:latest
```

This runs under Rosetta 2 and is slower but works. An arm64 Rasa image
exists too but isn't officially supported.

## 20. "My session directory is > 1GB"

`logs/trace.jsonl` grew unboundedly across many runs. Cleanup:

```
make clean                  # deletes only local session artifacts
```

If you want to keep some sessions but not all, pass their paths:

```
rm -rf ~/.local/share/sovereign-agent/homework/ex5/sess_<old>
```

---

## Didn't find your error?

1. `grep` the exact error message in this file.
2. Search `#module1-agents` — someone else may have asked today.
3. Open an issue on the homework repo with the `troubleshooting` label
   and paste the FULL error output. Screenshots are harder to search
   than plain text.
