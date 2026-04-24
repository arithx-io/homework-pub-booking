# Setup on macOS

## Prerequisites

Recommended: Homebrew. If you don't have it:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Python 3.12

The easiest way is to let `uv` manage it — skip ahead and run `make setup`,
which triggers `uv python install 3.12`.

Manual install (if you want Python 3.12 on your system PATH):

```
brew install python@3.12
```

## uv

```
brew install uv
```

Or the official installer:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Docker (only needed for Ex6)

Download **Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop/).
Open it once after install so the daemon starts.

Apple Silicon (M1/M2/M3) note: the Rasa image is x86. It will run under
Rosetta 2, which Docker Desktop auto-installs. Slower than native arm64
but works.

## Audio (only needed for Ex8 voice mode)

macOS comes with working audio. Grant Terminal/iTerm microphone access
when prompted: **System Settings → Privacy & Security → Microphone**.

## Common macOS traps

- **Apple Silicon + Rosetta**: if `uv sync` complains about incompatible
  architectures on some wheel, force x86 with `arch -x86_64 uv sync`.
- **xcode-select**: first-time installs may prompt for command-line tools.
  Accept — they take 10 minutes but one-off.
- **Firewall popups during `make verify`**: macOS asks whether Python is
  allowed to accept incoming connections. Say "Allow" (it's the openai
  client, not incoming).
