#!/usr/bin/env bash
# Module 08: shell reskin — ZorinAI-Dark shell theme + white category icons.
#
# Derives a full GNOME Shell theme from the installed Zorin dark shell CSS,
# sharpens the measured border radii (>=10px -> 4px, pills -> 4px, 5-9px -> 3px)
# and appends a cyberpunk-neon override block (dark menus, pink/purple/green
# accents). Activates it through the user-theme extension. Also installs solid
# white category icons so every icon in the start menu matches.
set -Eeuo pipefail
source "$REPO_ROOT/install/lib.sh"

BASE_THEME="/usr/share/themes/ZorinBlue-Dark"
THEME_NAME="ZorinAI-Dark"
THEME_DIR="/usr/share/themes/$THEME_NAME"

log "Building $THEME_NAME shell theme from ZorinBlue-Dark..."
if [ ! -f "$BASE_THEME/gnome-shell/gnome-shell.css" ]; then
  warn "ZorinBlue-Dark shell CSS not found — reskin skipped"
  exit 0
fi

sudo mkdir -p "$THEME_DIR/gnome-shell"
sudo cp -r "$BASE_THEME/gnome-shell/." "$THEME_DIR/gnome-shell/"

# Patch: clamp border radii + append neon overrides.
sudo python3 - "$THEME_DIR/gnome-shell/gnome-shell.css" <<'PYEOF'
import re
import sys

path = sys.argv[1]
css = open(path).read()


def clamp_radius(match):
    v = int(match.group(1))
    if v >= 999:
        v = 4
    elif v >= 10:
        v = 4
    elif v >= 5:
        v = 3
    return f"border-radius: {v}px"


css = re.sub(r"border-radius:\s*(\d+)px", clamp_radius, css)

css += """

/* ==== zorin-ai cyberpunk overrides ==== */
.popup-menu-content, .candidate-popup-content {
  background-color: rgba(7, 9, 14, 0.97);
  border: 1px solid rgba(255, 45, 149, 0.35);
  border-radius: 4px;
  color: #f2f2f7;
}
.popup-menu-item.selected {
  background-color: rgba(161, 36, 255, 0.22);
  border-radius: 3px;
  color: #ffffff;
}
.popup-menu-item:checked { background-color: rgba(57, 255, 136, 0.14); }
.popup-sub-menu {
  background-color: rgba(13, 16, 24, 0.98);
  border-radius: 3px;
}
.popup-menu-item { color: #e8e8f0; }
.search-entry {
  border-radius: 3px;
  border: 1px solid rgba(255, 45, 149, 0.35);
  color: #f2f2f7;
}
.search-entry:focus {
  border-color: rgba(255, 45, 149, 0.8);
  box-shadow: 0 0 6px rgba(255, 45, 149, 0.35);
}
StEntry { selection-background-color: rgba(161, 36, 255, 0.45); }
StScrollBar-StBin { background-color: rgba(161, 36, 255, 0.25); }
"""
open(path, "w").write(css)
print("patched:", path)
PYEOF

# Activate through the user-theme extension (applies on next shell reload/login).
if as_user gsettings list-schemas 2>/dev/null | grep -q '^org\.gnome\.shell\.extensions\.user-theme$'; then
  as_user gsettings set org.gnome.shell.extensions.user-theme name "$THEME_NAME" \
    || warn "could not set user-theme"
  log "OK: user-theme set to $THEME_NAME (dark menus, 4px facets, neon accents)"
else
  warn "user-theme extension schema missing — shell theme not activated"
fi

log "Switching GTK accent to ZorinPurple-Dark..."
if [ -d /usr/share/themes/ZorinPurple-Dark ]; then
  # NB: no `gs` helper here — module 06 defines one locally; bare `gs` would
  # resolve to the Ghostscript binary.
  as_user gsettings set org.gnome.desktop.interface gtk-theme 'ZorinPurple-Dark' \
    || warn "gtk-theme set failed"
fi

log "Installing solid white menu icons..."
ICON_DIR="/usr/local/share/icons/hicolor/scalable/apps"
sudo mkdir -p "$ICON_DIR"
for i in "$REPO_ROOT"/assets/icons/overrides/*.svg; do
  [ -f "$i" ] && sudo install -m 644 "$i" "$ICON_DIR/$(basename "$i")"
done
for i in "$REPO_ROOT"/assets/icons/zorin-ai-*.svg; do
  [ -f "$i" ] && sudo install -m 644 "$i" "$ICON_DIR/$(basename "$i")"
done
sudo gtk-update-icon-cache -q -t -f /usr/local/share/icons/hicolor 2>/dev/null || true
log "Shell reskin complete — sign out/in (or reboot) to see every change."
