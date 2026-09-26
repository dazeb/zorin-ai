#!/usr/bin/env bash
# Module 06: desktop customization — Windows/KDE ergonomics on Zorin.
# Every step is warn-not-die: a schema drift must never abort the install.
set -Eeuo pipefail
source "$REPO_ROOT/install/lib.sh"

gs() { as_user gsettings set "$@" 2>/dev/null || warn "gsettings failed: $*"; }

log "Window buttons to the right (Minimize, Maximize, Close)..."
gs org.gnome.desktop.wm.preferences button-layout ':minimize,maximize,close'

log "Enabling system dark mode..."
gs org.gnome.desktop.interface color-scheme 'prefer-dark'
gs org.gnome.desktop.interface gtk-theme 'ZorinBlue-Dark'

log "Pinning taskbar favorites (existing entries only)..."
CANDIDATES=(
  zorin-menu.desktop
  org.gnome.Nautilus.desktop
  codium.desktop
  xyz.chatboxapp.app.desktop
  io.missioncenter.MissionCenter.desktop
  org.gnome.Terminal.desktop
)
favorites=()
for c in "${CANDIDATES[@]}"; do
  if desktop_file_exists "$c"; then
    favorites+=("$c")
  else
    warn "Skipping missing desktop entry: $c"
  fi
done
if [ "${#favorites[@]}" -gt 0 ]; then
  gvariant="[$(printf "'%s'," "${favorites[@]}" | sed 's/,$//')]"
  gs org.gnome.shell favorite-apps "$gvariant"
  log "Favorites: ${favorites[*]}"
fi

log "Applying omarchy-style wallpaper set..."
WALLPAPER_DIR="/usr/local/share/backgrounds/zorin-ai"
sudo mkdir -p "$WALLPAPER_DIR"
for wp in "$REPO_ROOT"/assets/wallpapers/*.jpg; do
  [ -f "$wp" ] || continue
  sudo install -m 644 "$wp" "$WALLPAPER_DIR/$(basename "$wp")"
done
# Default: the moonlit ridge scene, for light and dark modes plus lock screen.
DEFAULT_WP="$WALLPAPER_DIR/zorin-ai-midnight-ridges-2160p.jpg"
if [ -f "$DEFAULT_WP" ]; then
  gs org.gnome.desktop.background picture-uri "file://$DEFAULT_WP"
  gs org.gnome.desktop.background picture-uri-dark "file://$DEFAULT_WP"
  gs org.gnome.desktop.background picture-options 'zoom'
  gs org.gnome.desktop.screensaver picture-uri "file://$WALLPAPER_DIR/zorin-ai-ember-minimal-2160p.jpg"
  log "Wallpaper set (cycle with: zom bg next)"
fi

log "Setting accent color (omarchy-style muted blue)..."
gs org.gnome.desktop.interface accent-color 'teal'

if as_user gsettings list-schemas 2>/dev/null | grep -q '^org\.gnome\.shell\.extensions\.ding$'; then
  log "Ensuring desktop icons (DING) show Home and Trash..."
  gs org.gnome.shell.extensions.ding show-home true
  gs org.gnome.shell.extensions.ding show-trash true
fi

log "Desktop customization complete (some settings may need a re-login to fully apply)."
