#!/usr/bin/env bash
# Computer Use Linux kurulum — wrapper'ları kurar, bağımlılıkları kontrol eder.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${CUL_BIN:-$HOME/bin}"
mkdir -p "$BIN"

echo "Computer Use Linux kurulumu"
echo "  proje : $ROOT"
echo "  bin   : $BIN"
echo

# --- wrapper: computer-use-linux (CLI) ---
cat > "$BIN/computer-use-linux" <<EOF
#!/bin/bash
export PYTHONPATH="$ROOT/core:$ROOT/adapters/cli:\$PYTHONPATH"
exec python3 "$ROOT/adapters/cli/computer_use_linux_cli.py" "\$@"
EOF
chmod +x "$BIN/computer-use-linux"

# --- wrapper: computer-use-linux-agent (metin protokolü) ---
cat > "$BIN/computer-use-linux-agent" <<EOF
#!/bin/bash
export PYTHONPATH="$ROOT/core:$ROOT/adapters/cli:\$PYTHONPATH"
exec python3 "$ROOT/adapters/cli/agent_loop.py" "\$@"
EOF
chmod +x "$BIN/computer-use-linux-agent"

# --- wrapper: computer-use-linux-http ---
cat > "$BIN/computer-use-linux-http" <<EOF
#!/bin/bash
export PYTHONPATH="$ROOT/core:\$PYTHONPATH"
exec python3 "$ROOT/adapters/http/server.py" "\$@"
EOF
chmod +x "$BIN/computer-use-linux-http"

# --- wrapper: computer-use-linux-mcp ---
cat > "$BIN/computer-use-linux-mcp" <<EOF
#!/bin/bash
export PYTHONPATH="$ROOT/core:$ROOT/adapters/mcp:\$PYTHONPATH"
exec python3 "$ROOT/adapters/mcp/server.py" "\$@"
EOF
chmod +x "$BIN/computer-use-linux-mcp"

echo "✓ wrapper'lar kuruldu: computer-use-linux, computer-use-linux-agent, computer-use-linux-http, computer-use-linux-mcp"
echo

# --- bağımlılık kontrolü ---
chk() { if command -v "$1" >/dev/null 2>&1; then echo "  ✓ $1"; else echo "  ✗ $1 — $2"; fi; }
pychk() { if python3 -c "$1" >/dev/null 2>&1; then echo "  ✓ $2"; else echo "  ✗ $2 — $3"; fi; }
echo "Bağımlılıklar (ayrıntı: docs/DEPENDENCIES.md):"
pychk "import dbus; import gi; gi.require_version('Gio','2.0')" "D-Bus (python3-dbus, python3-gi)" "sudo apt install python3-dbus python3-gi"
pychk "import gi; gi.require_version('Atspi','2.0'); from gi.repository import Atspi" "AT-SPI öğe ağacı" "sudo apt install gir1.2-atspi-2.0"
busctl --user get-property org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop \
    org.freedesktop.portal.RemoteDesktop version >/dev/null 2>&1 \
    && echo "  ✓ RemoteDesktop portalı (fare+klavye)" \
    || echo "  ✗ RemoteDesktop portalı — sudo apt install xdg-desktop-portal-kde pipewire"
pychk "import gi; gi.require_version('Gst','1.0'); from gi.repository import Gst; Gst.init(None); assert Gst.ElementFactory.find('pipewiresrc')" \
    "hızlı ekran görüntüsü (GStreamer pipewiresrc, ~0.1 sn)" "sudo apt install gstreamer1.0-pipewire (yoksa portal: ~1.5 sn)"
chk wl-copy   "Türkçe/emoji yazma için: sudo apt install wl-clipboard"
chk tmux      "terminal oturumları için: sudo apt install tmux (yoksa PTY)"
command -v spectacle >/dev/null 2>&1 || command -v grim >/dev/null 2>&1 \
    && echo "  ✓ ekran görüntüsü (spectacle/grim)" \
    || echo "  ✗ ekran görüntüsü — sudo apt install spectacle"
pychk "import PIL" "Pillow (kırp/küçült)" "sudo apt install python3-pil"
pychk "import Xlib" "python-xlib (görünür ajan imleci)" "sudo apt install python3-xlib"
pychk "import mcp" "mcp (MCP adaptörü, opsiyonel)" "pip install mcp"

echo
if ! echo ":$PATH:" | grep -q ":$BIN:"; then
  echo "⚠  $BIN PATH'te değil. Kabuk profiline ekle:"
  echo "     export PATH=\"$BIN:\$PATH\""
fi
echo "Sonraki adım:  computer-use-linux setup   (KDE bir kez 'Uzaktan kontrol' izni sorar)"
echo "MCP (Claude Code): claude mcp add computer-use-linux -- $BIN/computer-use-linux-mcp"
