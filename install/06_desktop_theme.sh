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

if as_user gsettings list-schemas 2>/dev/null | grep -q '^org\.gnome\.shell\.extensions\.ding$'; then
  log "Ensuring desktop icons (DING) show Home and Trash..."
  gs org.gnome.shell.extensions.ding show-home true
  gs org.gnome.shell.extensions.ding show-trash true
fi

log "Desktop customization complete (some settings may need a re-login to fully apply)."
