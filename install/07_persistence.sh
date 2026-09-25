#!/usr/bin/env bash
# Module 07: persistence — /etc/skel defaults for new users + zom management CLI.
set -Eeuo pipefail
source "$REPO_ROOT/install/lib.sh"

log "Syncing defaults into /etc/skel (applies to every user created from now on)..."
sudo mkdir -p \
  /etc/skel/.config/mise \
  /etc/skel/.continue \
  /etc/skel/.local/share/nautilus/scripts

sudo install -m 644 "$REPO_ROOT/configs/mise/config.toml" \
  /etc/skel/.config/mise/config.toml
sudo install -m 644 "$REPO_ROOT/configs/vscodium/continue_config.yaml" \
  /etc/skel/.continue/config.yaml
for src in "$REPO_ROOT/configs/nautilus-scripts/"*; do
  [ -f "$src" ] || continue
  sudo install -m 755 "$src" "/etc/skel/.local/share/nautilus/scripts/$(basename "$src")"
done
sudo chmod -R go+rX /etc/skel/.config /etc/skel/.continue /etc/skel/.local

log "Installing zom management CLI..."
sudo install -m 755 "$REPO_ROOT/bin/zom" /usr/local/bin/zom
sudo install -m 755 "$REPO_ROOT/bin/zom-menu" /usr/local/bin/zom-menu

sudo mkdir -p /usr/local/share/applications
sudo tee /usr/local/share/applications/zom-menu.desktop >/dev/null <<'EOF'
[Desktop Entry]
Type=Application
Name=zorin-ai Control Panel
Comment=Update and health-check your zorin-ai workstation
Exec=zom-menu
Icon=applications-system
Terminal=false
Categories=System;
EOF

log "Persistence complete: new users inherit mise, Continue and Nautilus script defaults."
log "Manage the workstation with: zom (CLI) or zom-menu (GUI)."
