#!/usr/bin/env bash
# İzole, başsız GERÇEK GNOME Shell (Mutter): kendi D-Bus'ı, kendi XDG_RUNTIME_DIR'ı,
# kendi PipeWire'ı. Kullanıcının oturumuna dokunmaz. gnome-shell yoksa 77 ile çıkar (atla).
#
#   tests/gnome_sandbox.sh <komut...>
#
# Gerekli paketler (Debian 13): gnome-shell xdg-desktop-portal-gnome pipewire wireplumber
#   at-spi2-core python3-gi gir1.2-gtk-3.0 python3-dbusmock
#   gstreamer1.0-pipewire gstreamer1.0-plugins-good gstreamer1.0-tools wl-clipboard (ekran görüntüsü/pano)
# gnome-shell sistem veriyolunda logind ister; kullanıcı oturumuna dokunmamak için
# özel bir sistem veriyolu + sahte logind (python3-dbusmock) başlatılır.
set -euo pipefail
for b in gnome-shell pipewire; do
    command -v "$b" >/dev/null || { echo "$b yok — atlandı"; exit 77; }
done
[[ -x /usr/libexec/xdg-desktop-portal ]] || { echo "xdg-desktop-portal yok — atlandı"; exit 77; }
[[ -x /usr/libexec/xdg-desktop-portal-gnome ]] || { echo "xdg-desktop-portal-gnome yok — atlandı"; exit 77; }

if [[ "${CUL_GNOME_INNER:-}" != 1 ]]; then
    export CUL_GNOME_INNER=1
    exec dbus-run-session -- "$0" "$@"
fi

ROOT="$(mktemp -d /tmp/cul-gnome.XXXXXX)"
chmod 700 "$ROOT"
mkdir -p "$ROOT"/{run,config,data,cache}
export XDG_RUNTIME_DIR="$ROOT/run" XDG_CONFIG_HOME="$ROOT/config" \
       XDG_DATA_HOME="$ROOT/data" XDG_CACHE_HOME="$ROOT/cache"
export XDG_CURRENT_DESKTOP=GNOME XDG_SESSION_TYPE=wayland CUL_SANDBOX=1 CUL_GNOME=1
export CUL_INPUT_BACKEND=${CUL_INPUT_BACKEND-mutter}
export GTK_A11Y=atspi NO_AT_BRIDGE=0 WAYLAND_DISPLAY="cul-gnome-$$"
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

python3 -c 'import dbusmock' 2>/dev/null || { echo "python3-dbusmock yok — atlandı"; exit 77; }
cat > "$ROOT/system.conf" <<CONF
<busconfig><type>system</type><listen>unix:path=$ROOT/sysbus</listen><auth>EXTERNAL</auth>
<policy context="default"><allow send_destination="*" eavesdrop="true"/><allow eavesdrop="true"/><allow own="*"/></policy></busconfig>
CONF
dbus-daemon --config-file="$ROOT/system.conf" --nofork --nopidfile >"$ROOT/sysbus.log" 2>&1 & pids+=($!)
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=$ROOT/sysbus"
for _ in $(seq 50); do [[ -S "$ROOT/sysbus" ]] && break; sleep 0.1; done
python3 -m dbusmock --system -t logind >"$ROOT/logind.log" 2>&1 & pids+=($!)
for _ in $(seq 50); do busctl --system status org.freedesktop.login1 >/dev/null 2>&1 && break; sleep 0.1; done

pipewire >"$ROOT/pipewire.log" 2>&1 & pids+=($!)
wireplumber >"$ROOT/wireplumber.log" 2>&1 & pids+=($!)
for _ in $(seq 50); do [[ -S "$XDG_RUNTIME_DIR/pipewire-0" ]] && break; sleep 0.1; done

LIBGL_ALWAYS_SOFTWARE=1 gnome-shell --headless --wayland --no-x11 --virtual-monitor 1280x800 \
    --wayland-display "$WAYLAND_DISPLAY" >"$ROOT/gnome-shell.log" 2>&1 &
pids+=($!)
for _ in $(seq 150); do [[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]] && break; sleep 0.1; done
[[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]] || { echo "gnome-shell başlamadı"; tail -20 "$ROOT/gnome-shell.log"; exit 1; }
for _ in $(seq 100); do
    busctl --user status org.freedesktop.portal.Desktop >/dev/null 2>&1 && break; sleep 0.1
done

export CUL_SANDBOX_LOGS="$ROOT"
"$@"
