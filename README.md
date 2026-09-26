# zorin-ai

Mouse-first AI developer workstation provisioner for **Zorin OS 17+** (Ubuntu LTS base),
in the spirit of [Omakub](https://omakub.org) — but with **full mouse parity**:
no task requires opening a terminal.

One command on a fresh Zorin machine:

```bash
curl -fsSL https://raw.githubusercontent.com/dazeb/zorin-ai/main/boot.sh | bash
```

## What you get

| Area | Software |
|------|----------|
| Local AI | [Ollama](https://ollama.com) on `127.0.0.1:11434` + `qwen2.5-coder:7b` and the `nomic-embed-text` embedding model, wired into everything below |
| Editor | [VSCodium](https://vscodium.com) with Continue.dev, GitLens, Prettier, Python, Go extensions |
| Chat GUI | [Chatbox](https://chatboxai.app) desktop client (official `.deb`) |
| Task manager | Mission Center (Flathub) — Windows-Task-Manager-style |
| Runtimes | [mise](https://mise.jdx.dev) managing Node LTS, Python 3.12, Go system-wide |
| Mouse ergonomics | Nautilus right-click: *Open in VSCodium*, *Ask AI to Explain*, *Open Terminal Here* |
| Desktop | Windows/KDE-style window buttons, dark mode, pinned taskbar favorites, desktop icons, omarchy-style procedural wallpaper set (`zom bg next` cycles it) |
| Maintenance | `zom` CLI + `zom-menu` GUI panel (`update`, `doctor`, `models`) |
| Persistence | `/etc/skel` defaults for every new user |

## Layout

```
boot.sh              remote fetcher / repo updater
install.sh           orchestrator (flags: --skip-ai, --skip-gui)
install/             modules 00–07 + lib.sh
bin/                 zom, zom-menu
configs/             mise, VSCodium, Continue, Nautilus script configs
iso/                 build-zorin-ai-iso.sh — remaster Zorin into a bootable
                     Zorin-AI OS ISO with first-boot auto-provisioning
```

See [PLAN.md](PLAN.md) for the full build plan, verified software inventory,
and design deviations from the source spec.

## Maintenance

```bash
zom update        # apt + flatpak + mise runtimes + AI models
zom doctor        # health check (Ollama, mise, VSCodium, GPU, disk)
zom models gui    # pick & download models from a GUI list
zom bg next       # cycle the omarchy-style wallpaper set
zom-menu          # the same things, mouse-driven
```

## Flags

```bash
./boot.sh --skip-ai     # everything except Ollama/model download
./boot.sh --skip-gui    # headless-ish: skip GUI apps, Nautilus and theme steps
ZORIN_AI_MODEL=llama3.2:3b ./boot.sh   # different default model
```

## Status

**Phase 1 provisioner is VM-validated.** Installed end-to-end on a clean Zorin OS 18.1
VM (Proxmox): four installer runs including one interrupted by a host reboot — the
installer resumed cleanly and re-runs are no-ops (idempotence proven). `zom doctor`
all green; runtimes, extensions, Flatpaks, Chatbox, gsettings and `/etc/skel`
defaults all verified. Remaining: interactive GUI walkthrough (M3) and release
polish (M4). See [PLAN.md](PLAN.md) §7 for milestone detail.
