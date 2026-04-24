# Setup on Linux

Distros verified: Ubuntu 22.04+, Debian 12+, Fedora 39+.

## Python 3.12

### Ubuntu / Debian

```
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

If your distro's apt repo doesn't have 3.12 yet, use deadsnakes PPA:

```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

### Fedora

```
sudo dnf install python3.12 python3.12-devel
```

### Arch / Manjaro

```
sudo pacman -S python
```

## uv

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via pip:

```
python3.12 -m pip install --user uv
```

## Docker (only needed for Ex6)

### Ubuntu / Debian

```
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
# log out and back in, or:
newgrp docker
```

### Fedora

```
sudo dnf install -y docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Verify with:

```
docker run --rm hello-world
```

## Audio (only needed for Ex8 voice mode)

Most distros have PulseAudio / PipeWire out of the box. Test:

```
arecord -d 2 /tmp/test.wav && aplay /tmp/test.wav
```

If `arecord` isn't found, `sudo apt install alsa-utils` (Debian/Ubuntu)
or equivalent.

For the `sounddevice` Python package (used optionally by Ex8 voice):

```
sudo apt install -y portaudio19-dev libsndfile1
```

## Common Linux traps

- **`uv: command not found` after install**: `$HOME/.local/bin` not on PATH.
  Add to `~/.bashrc` or `~/.zshrc`:
  ```
  export PATH="$HOME/.local/bin:$PATH"
  ```
- **Permission denied on docker.sock**: you skipped the `usermod -aG docker`
  step or didn't log out/in.
- **WSL users should NOT follow this file**: use `docs/setup-windows.md`
  for WSL-specific notes.
