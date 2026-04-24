# Setup on Windows

**TL;DR: use WSL. Native Windows works for some exercises but will bite
you on Ex6 (Docker integration) and Ex8 (audio). WSL removes every known
trap.**

## WSL 2 setup (strongly recommended)

### Install WSL 2

Open PowerShell **as administrator**:

```
wsl --install -d Ubuntu-22.04
```

Reboot. When WSL finishes first-run setup, you have an Ubuntu shell.
From that point on, **everything you do for this homework happens inside
WSL**.

### Inside WSL

Follow `docs/setup-linux.md` from step 1. The Ubuntu instructions work
verbatim.

### Clone inside WSL, not on Windows

Clone into your WSL home, not onto `/mnt/c/...`:

```
# Inside WSL:
cd ~
git clone https://github.com/sovereignagents/homework-pub-booking.git
cd homework-pub-booking
```

Cloning onto `/mnt/c/` works but is ~10x slower for everything (uv sync,
pytest, Docker builds) because of filesystem translation.

### Editor

VS Code with the "WSL" extension is the standard setup. Open your WSL
terminal and run `code .` in the repo directory; VS Code launches with
the WSL filesystem mounted.

### Docker (for Ex6)

Install Docker Desktop on Windows. In Settings → Resources → WSL
Integration, enable it for your Ubuntu distro. You can then `docker ...`
from inside WSL.

### Audio (for Ex8 voice mode)

WSL 2 audio works via PulseAudio forwarding since Windows 11 22H2. If
you're on Windows 10, voice mode is fiddly — just run Ex8 in text mode
(`make ex8-text`); you can earn up to 16/20 on it that way.

---

## Native Windows (not recommended)

If you absolutely cannot use WSL (corporate policy, offline machine):

### Python 3.12

Install from [python.org](https://www.python.org/downloads/). Check
"Add Python to PATH" during installation.

### Git

Install [Git for Windows](https://git-scm.com/download/win). Use Git Bash
for all command-line work; PowerShell and cmd.exe quote arguments
differently and will produce confusing errors.

### uv

In Git Bash:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Make

Windows does not have `make` by default. Options:

1. **Git Bash** includes a limited `make` — works for most targets.
2. **Chocolatey**: `choco install make`.
3. **Scoop**: `scoop install make`.

### Known native-Windows limitations

- **Ex6 (Rasa + Docker)**: Docker Desktop is supported but volume mounts
  with Windows paths cause intermittent bind errors. WSL avoids this.
- **Ex8 voice mode**: `sounddevice` + Speechmatics real-time streaming
  works, but microphone permissions are fiddly. Text mode works fine.
- **Path separators**: if any tool error mentions `\\` in a path, you
  likely hit a forward/backward slash bug. WSL avoids this.

### Line endings

Git for Windows defaults to converting `LF → CRLF` on checkout. The
homework assumes LF. Configure git before your first clone:

```
git config --global core.autocrlf false
```

If you already cloned, re-clone after setting this.
