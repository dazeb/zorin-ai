# AGENTS.md — zorin-ai

Instructions for coding agents working in this repository. Read fully before
changing anything; the pitfalls section saves real debugging time.

## What this repo is

`zorin-ai` is an Omakub-style provisioner that turns a fresh **Zorin OS 18.x**
(Ubuntu 24.04 base) machine into a mouse-first **AI development workstation**:
local Ollama stack, a six-agent start menu, mise-managed runtimes, and a
cyberpunk visual theme (ZorinAI-Dark shell theme, neon polygonal wallpapers,
white icons). It also builds a bootable **Zorin-AI OS ISO** with all of this
baked in.

The repo is **public on GitHub** (`github.com/dazeb/zorin-ai`) — this is a hard
requirement: the one-liner bootstrap and the ISO's first-boot fetch clone it
anonymously. Never make it private, never commit secrets.

## Repository map

```
boot.sh                     remote fetcher: clones repo to ~/.local/share/zorin-ai,
                            runs install.sh; env: ZORIN_AI_REPO_URL, ZORIN_AI_BRANCH, ZORIN_AI_HOME
install.sh                  orchestrator: logging, TARGET_USER resolution, flags
                            (--skip-ai, --skip-gui), runs modules 00-07 + 08
install/
  lib.sh                    shared helpers: log/warn/die, as_user(), apt_install(),
                            desktop_file_exists(). Modules MUST source it.
  00_preflight.sh           user/sudo/OS/network/25GB-disk/RAM checks
  01_system.sh              apt core + python build deps, Flathub, Nerd Font
  02_mise.sh                mise binary, profile.d + bash.bashrc hooks, runtimes
  03_ai_core.sh             Ollama + qwen2.5-coder:7b + nomic-embed-text
  04_gui_apps.sh            VSCodium + extensions, Mission Center, Chatbox .deb
  05_mouse_ergonomics.sh    Nautilus right-click scripts
  06_desktop_theme.sh       gsettings ergonomics, wallpapers, Agents menu,
                            AI-first /etc/xdg/menus/gnome-applications.menu
  07_persistence.sh         /etc/skel defaults, zom + zom-menu install
  08_shell_theme.sh         ZorinAI-Dark shell theme (derived, not shipped),
                            white category icon overrides, GTK purple accent
bin/
  zom                       CLI: update | doctor | models [list|pull|rm|gui] | bg [list|next|set]
  zom-menu                  zenity control panel
  zorin-ai-agent            agent launcher wrapper: installs npm package on
                            first use, then execs the agent
configs/
  mise/config.toml          node=lts, python=3.12, go=latest
  vscodium/                 settings.json, extensions.list, continue_config.yaml
  copyq/copyq.conf          clipboard history preseed (1000 entries, silent, tray)
  autostart/copyq.desktop   CopyQ session autostart (user + /etc/skel)
  applications/             agent + Local-LLM .desktop launchers, .directory files
  xdg/                      gnome-applications.menu (AI-first tree), agents merge
  nautilus-scripts/         Open_in_VSCodium, Ask_AI_to_Explain, Open_Terminal_Here
assets/
  wallpapers/               5 seeded 4K JPEG scenes + generate-wallpapers.py
  icons/                    white SVG glyphs (agents, Local LLM, category tiles)
  icons/overrides/          white SVGs under STOCK icon names — these replace
                            the system category icons system-wide
iso/build-zorin-ai-iso.sh   ISO remaster pipeline (runs on the Proxmox node)
```

## Non-negotiable rules

1. **Never run `install.sh`/`boot.sh` on the local dev workstation.** This box
   (Ubuntu 26.04, `dazeb-ubuntubox`) is for editing and static checks only.
   All runtime testing happens on the Proxmox test VM.
2. **Every module must be idempotent.** Guard every mutation (`command -v`,
   file existence, `dpkg-query`, `gsettings get`). Re-running install.sh must
   be a no-op. There is a live test VM precisely to prove this.
3. **Desktop settings are warn-not-die.** `gsettings`/theme steps must never
   abort an install (`|| warn "..."`). Core steps (apt, ollama) may die.
4. **`gs` is a trap.** Module 06 defines a local `gs()` helper for gsettings.
   Other modules must NOT call bare `gs` — it resolves to the **Ghostscript
   binary**. Use `as_user gsettings set ...` explicitly.
5. **No `grep -q` on pipes under `set -o pipefail`** for large-output
   producers (`fc-list`, …): grep exits early, SIGPIPEs the producer, and the
   guard misreads "installed" as "missing". Drain with `grep ... >/dev/null`.
6. **gsettings must target the user session bus**, never `dbus-launch`:
   `as_user` in lib.sh handles it (DBUS_SESSION_BUS_ADDRESS=/run/user/UID/bus).
7. **Verify pushes server-side**: `gh api repos/dazeb/zorin-ai/commits/heads/main --jq .sha`.
   A clean `git push` exit code has already lied here once — check which branch
   HEAD is on (`git status`) and confirm the remote SHA after pushing.
8. **Working tree hygiene**: commit on `main`. If `git status` shows a feature
   branch you did not intentionally create, stop and reconcile before
   committing (this bit us: 6 commits landed on a stray branch unnoticed).
9. **Do not touch other guests on the Proxmox node** (VMs 107/108/113/114,
   LXC 100-112/200/210). VM 114 (`zorin-ai-iso-test`) is ours.
10. **Nautilus scripts get selections via env vars**
    (`NAUTILUS_SCRIPT_SELECTED_FILE_PATHS`), not argv. VNC-typed text into the
    guest loses shifted characters (`& @ > :`) — route anything complex
    through SSH or an HTTP fetch from port 80 (no colon in URL).

## Environment (infrastructure)

- **Proxmox node**: `ssh root@192.168.8.195` (key auth, host "files",
  PVE 9.2.20, i7-4770K / 15 GiB RAM). Web-UI password unknown — work over SSH.
- **Test VM**: VM 114 `zorin-ai-iso-test` at `192.168.8.187`, user `dazeb`,
  password `zorin-test-2026` (throwaway), our SSH key authorized,
  passwordless sudo via `/etc/sudoers.d/zai-test`. Booted from the v0.2 ISO
  and self-provisioned on first login — it is the living reference install.
- **ISO build** runs on the node, not here. Scratch MUST be on
  `/local-zfs` (`WORK_BASE=/local-zfs/iso-build`) — pve-root has ~8 GiB free
  and the build needs ~25 GiB. The zfs pool is HDD-backed: unsquashfs and
  mksquashfs take 10-20 min each; total build ~35-45 min. Run as a
  `systemd-run --unit=<name> --collect bash -c "..."` unit (plain nohup over
  ssh dies with the session). ISOs live in `/var/lib/vz/template/iso/`.
- **RAM pressure**: the node juggles 14 GiB of allocated VMs. Don't start
  extra VMs while builds run; builds peak ~2 GiB.
- `xorriso`, `git`, `squashfs-tools` are installed on the node (2026-09-25).

## Commands

```bash
# static checks (docker shellcheck — not installed on this host)
bash -n boot.sh install.sh install/*.sh bin/* configs/nautilus-scripts/*
docker run --rm -v "$PWD:/mnt" koalaman/shellcheck:stable --severity=warning \
  boot.sh install.sh install/*.sh bin/zom bin/zom-menu bin/zorin-ai-agent \
  configs/nautilus-scripts/*

# wallpaper iteration (venv at ~/workspace/scratch/zorin-img-venv: pillow+numpy)
cd assets/wallpapers
~/workspace/scratch/zorin-img-venv/bin/python generate-wallpapers.py \
  --width 1920 --height 1080 --outdir /tmp/wp-preview     # fast previews
~/workspace/scratch/zorin-img-venv/bin/python generate-wallpapers.py      # 4K final

# deploy a change to the test VM (idempotent full pass)
tar czf /tmp/zai-repo.tgz --exclude=.git --exclude=.zcodeignore .
scp -q /tmp/zai-repo.tgz dazeb@192.168.8.187:/tmp/
ssh dazeb@192.168.8.187 'rm -rf ~/.local/share/zorin-ai && mkdir -p ~/.local/share/zorin-ai \
  && tar xzf /tmp/zai-repo.tgz -C ~/.local/share/zorin-ai \
  && nohup bash ~/.local/share/zorin-ai/install.sh > /tmp/zai-run.log 2>&1 &'
# headless runs need NOPASSWD sudo (already enabled on VM 114) or cached creds

# fresh-clone audit + server-side push verification
git clone -q git@github.com:dazeb/zorin-ai.git /tmp/zai-clone && find /tmp/zai-clone -type f | wc -l
gh api repos/dazeb/zorin-ai/commits/heads/main --jq '.sha[0:7] + " " + .commit.message'

# ISO build (on the node)
ssh root@192.168.8.195
systemd-run --unit=zai-iso --collect bash -c \
  "WORK_BASE=/local-zfs/iso-build bash /local-zfs/iso-build/build-zorin-ai-iso.sh \
   /var/lib/vz/template/iso/Zorin-OS-18.1-Core-64-bit.iso \
   /var/lib/vz/template/iso/zorin-ai-os-18.1-amd64.iso > /local-zfs/iso-build/build.log 2>&1"
tail -f /local-zfs/iso-build/build.log
```

## Known pitfalls (each cost real debugging time)

- **xorriso refuses non-empty `-outdev`** ("media holds non-zero data"):
  the build script `rm -f`s the previous ISO before writing. Do not remove
  that line; do not silence xorriso's output.
- **`sudo -v` needs a TTY even under NOPASSWD sudoers** — headless preflight
  uses `sudo -n true` first. Keep that fallback order.
- **Chatbox package/desktop ids are `xyz.chatboxapp.app`** (not the old
  Flathub id `xyz.chatboxapp.Chatbox`, which is dead — the vendor CDN
  `.deb` is the channel).
- **`zorin-menu.desktop` does not exist on Zorin 18**; favorites and menu
  code skip missing desktop entries by design.
- **`org.gnome.desktop.interface accent-color` key is absent** on Zorin 18.1 —
  the attempt warns and moves on.
- **Menu tree changes need a session rescan** (logout or reboot). Wayland has
  no in-place shell restart.
- **VNC typing into the VM console drops/mangles shifted characters** and
  rapid reconnects fail silently; vncdotool exit codes are always 1. Prefer
  SSH once sshd is up; use QEMU monitor `sendkey` for exact console input.
- **The first-boot runner falls back to the baked snapshot when `git` is
  absent** (fresh installs). Provisioner now installs openssh-server in
  module 01 for post-install remote access.

## Verification checklist for any change

1. `bash -n` + shellcheck (docker) clean on touched scripts.
2. Fresh-clone audit: clone from GitHub, confirm new files exist.
3. Deploy to VM 114, full installer run, confirm green + idempotent second run.
4. If menus/theme changed: reboot the VM and check the session visuals.
5. If ISO-relevant: rebuild ISO on the node, boot-test to the installer
   screen (live session gets DHCP = squashfs valid), then restore VM 114.
6. Push, then verify the remote SHA server-side.

## Current state (2026-09-26)

- `main` at v0.2.0; VM 114 runs the fully provisioned reference install.
- ISO v0.2 on the node: sha256 `d747f013…` (see `.sha256` file next to it).
- Roadmap ideas: unattended installer preseeding, Aider/Goose launchers
  (non-npm install paths), custom branding assets, GTK corner-radius work.
