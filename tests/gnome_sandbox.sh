#!/usr/bin/env bash
# İzole, başsız GERÇEK GNOME Shell (Mutter): kendi D-Bus'ı, kendi XDG_RUNTIME_DIR'ı,
# kendi PipeWire'ı. Kullanıcının oturumuna dokunmaz. gnome-shell yoksa 77 ile çıkar (atla).
#
#   tests/gnome_sandbox.sh <komut...>
#
# Gerekli paketler (Debian 13): gnome-shell xdg-desktop-portal-gnome pipewire wireplumber
#   at-spi2-core python3-gi gir1.2-gtk-3.0
set -euo pipefail
for b in gnome-shell xdg-desktop-portal pipewire; do
    command -v "$b" >/dev/null || { echo "$b yok — atlandı"; exit 77; }
done
[[ -x /usr/libexec/xdg-desktop-portal-gnome ]] || { echo "xdg-desktop-portal-gnome yok — atlandı"; exit 77; }

if [[ "${NEXR_GNOME_INNER:-}" != 1 ]]; then
    export NEXR_GNOME_INNER=1
    exec dbus-run-session -- "$0" "$@"
fi

ROOT="$(mktemp -d /tmp/nexr-gnome.XXXXXX)"
chmod 700 "$ROOT"
mkdir -p "$ROOT"/{run,config,data,cache}
export XDG_RUNTIME_DIR="$ROOT/run" XDG_CONFIG_HOME="$ROOT/config" \
       XDG_DATA_HOME="$ROOT/data" XDG_CACHE_HOME="$ROOT/cache"
export XDG_CURRENT_DESKTOP=GNOME XDG_SESSION_TYPE=wayland NEXR_SANDBOX=1 NEXR_GNOME=1
export GTK_A11Y=atspi NO_AT_BRIDGE=0 WAYLAND_DISPLAY="nexr-gnome-$$"
unset DISPLAY SWAYSOCK HYPRLAND_INSTANCE_SIGNATURE KDE_FULL_SESSION
dbus-update-activation-environment XDG_RUNTIME_DIR XDG_CONFIG_HOME XDG_DATA_HOME \
    XDG_CACHE_HOME XDG_CURRENT_DESKTOP XDG_SESSION_TYPE WAYLAND_DISPLAY GTK_A11Y NO_AT_BRIDGE

pids=()
cleanup() {
    for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done
    wait 2>/dev/null || true
    fusermount3 -u "$ROOT/run/doc" 2>/dev/null || fusermount -u "$ROOT/run/doc" 2>/dev/null || true
    rm -rf "$ROOT" 2>/dev/null || true
}
trap cleanup EXIT

pipewire >"$ROOT/pipewire.log" 2>&1 & pids+=($!)
wireplumber >"$ROOT/wireplumber.log" 2>&1 & pids+=($!)
for _ in $(seq 50); do [[ -S "$XDG_RUNTIME_DIR/pipewire-0" ]] && break; sleep 0.1; done

gnome-shell --headless --wayland --no-x11 --virtual-monitor 1280x800 \
    --wayland-display "$WAYLAND_DISPLAY" >"$ROOT/gnome-shell.log" 2>&1 &
pids+=($!)
for _ in $(seq 150); do [[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]] && break; sleep 0.1; done
[[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]] || { echo "gnome-shell başlamadı"; tail -20 "$ROOT/gnome-shell.log"; exit 1; }
for _ in $(seq 100); do
    busctl --user status org.freedesktop.portal.Desktop >/dev/null 2>&1 && break; sleep 0.1
done

export NEXR_SANDBOX_LOGS="$ROOT"
"$@"
