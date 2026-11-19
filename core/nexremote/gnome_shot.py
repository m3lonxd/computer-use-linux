"""GNOME'da ekran görüntüsü yedekleri (gnome-screenshot yoksa).

org.gnome.Shell.Screenshot GNOME 41'den beri yalnızca izinli çağıranlara açık
(diğerleri AccessDenied alır). İki yol kalır:

  mutter   NEXREMOTE_INPUT_BACKEND=mutter ile açıkça seçilmişse: izinsiz Mutter
           ScreenCast (tüm ekran alanı) + gst-launch-1.0 pipewiresrc ile tek kare.
  portal   org.freedesktop.portal.Screenshot (interactive=false); GNOME ilk
           kullanımda kullanıcıdan izin ister.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import Optional


def mutter_available() -> bool:
    return bool(shutil.which("gst-launch-1.0"))


def mutter_grab(path: str, timeout: float = 20.0) -> None:
    """Mutter ScreenCast'ten tek kare alıp PNG olarak path'e yazar."""
    import dbus
    from gi.repository import GLib
    from ._dbus import session_bus
    from .portal_input import MutterSession

    bus = session_bus()
    mons = MutterSession._monitors(_Probe(bus))
    if not mons:
        raise RuntimeError("GNOME Shell monitör listesi boş")
    x0 = min(m["x"] for m in mons)
    y0 = min(m["y"] for m in mons)
    x1 = max(m["x"] + m["w"] for m in mons)
    y1 = max(m["y"] + m["h"] for m in mons)
    sc = dbus.Interface(bus.get_object(MutterSession.SC, "/org/gnome/Mutter/ScreenCast"),
                        MutterSession.SC)
    sess_path = str(sc.CreateSession({}))
    sess = dbus.Interface(bus.get_object(MutterSession.SC, sess_path), MutterSession.SC + ".Session")
    try:
        stream_path = str(sess.RecordArea(x0, y0, x1 - x0, y1 - y0, {}))
        box: dict = {}
        loop = GLib.MainLoop()

        def on_node(node):
            box["node"] = int(node)
            loop.quit()

        bus.add_signal_receiver(on_node, "PipeWireStreamAdded", MutterSession.SC + ".Stream",
                                MutterSession.SC, stream_path)
        sess.Start()
        GLib.timeout_add(int(timeout * 1000), loop.quit)
        loop.run()
        if "node" not in box:
            raise RuntimeError("Mutter ScreenCast PipeWire düğümü vermedi")
        if os.path.exists(path):
            os.remove(path)
        r = subprocess.run(["gst-launch-1.0", "-q", "pipewiresrc", f"path={box['node']}",
                            "num-buffers=2", "!", "videoconvert", "!", "pngenc", "snapshot=true",
                            "!", "filesink", f"location={path}"],
                           capture_output=True, timeout=timeout)
        if r.returncode != 0:
            raise RuntimeError("gst-launch-1.0 pipewiresrc başarısız: "
                               + r.stderr.decode("utf-8", "replace").strip()[-200:])
    finally:
        try:
            sess.Stop()
        except Exception:
            pass


class _Probe:
    """MutterSession._monitors için yalnızca bus/dbus taşıyan sahte nesne."""

    def __init__(self, bus) -> None:
        import dbus
        self.dbus = dbus
        self.bus = bus


def portal_grab(path: str, timeout: float = 90.0) -> None:
    """xdg-desktop-portal Screenshot (etkileşimsiz). İlk kullanımda izin diyaloğu çıkar."""
    import dbus
    from gi.repository import GLib
    from urllib.parse import unquote, urlparse
    from ._dbus import session_bus

    bus = session_bus()
    obj = bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
    token = f"nexshot{os.getpid()}_{int(time.time())}"
    sender = bus.get_unique_name()[1:].replace(".", "_")
    box: dict = {}
    loop = GLib.MainLoop()

    def on_resp(code, results):
        box["code"], box["results"] = int(code), results
        loop.quit()

    m = bus.add_signal_receiver(on_resp, "Response", "org.freedesktop.portal.Request",
                                "org.freedesktop.portal.Desktop",
                                f"/org/freedesktop/portal/desktop/request/{sender}/{token}")
    try:
        dbus.Interface(obj, "org.freedesktop.portal.Screenshot").Screenshot(
            "", {"handle_token": token, "interactive": dbus.Boolean(False)})
        GLib.timeout_add(int(timeout * 1000), loop.quit)
        loop.run()
    finally:
        m.remove()
    if "code" not in box:
        raise TimeoutError("portal ekran görüntüsü vermedi (izin diyaloğu açık kalmış olabilir)")
    if box["code"] != 0:
        raise PermissionError("ekran görüntüsü izni verilmedi")
    uri: Optional[str] = str(box["results"].get("uri", ""))
    src = unquote(urlparse(uri).path) if uri else ""
    if not src or not os.path.exists(src):
        raise RuntimeError("portal dosya yolu döndürmedi")
    shutil.copyfile(src, path)
