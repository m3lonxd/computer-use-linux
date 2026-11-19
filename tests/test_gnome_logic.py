#!/usr/bin/env python3
"""GNOME mantığı — gerçek GNOME gerekmez (sahte D-Bus). Salt okuma, her yerde koşar.

Regresyonlar (gerçek GNOME 48.7'de bulundu): Latin-1 harfler (ü, é) Mutter'da US
düzeninde tuşlanamaz → panodan yapıştırılmalı; Mutter monitör listesi doğru
ayrıştırılmalı; GNOME'da ekran görüntüsü yedeği seçilmeli.
"""
import os
import shutil
import sys
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core"))
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"  {'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail else ""))


from nexremote import portal_input as pi  # noqa: E402

with mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"}):
    check("GNOME: ASCII tuşlanır", pi._keyable("a") and pi._keyable("\n"))
    check("GNOME: ü/é panodan (tuşlanamaz)", not pi._keyable("ü") and not pi._keyable("é"))
with mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}):
    check("KDE: Latin-1 eskisi gibi tuşlanır", pi._keyable("ü"))

with mock.patch.dict(os.environ, {"NEXREMOTE_INPUT_BACKEND": "mutter"}):
    check("NEXREMOTE_INPUT_BACKEND=mutter seçilir", pi.use_mutter())
with mock.patch.dict(os.environ, {}, clear=False):
    os.environ.pop("NEXREMOTE_INPUT_BACKEND", None)
    check("varsayılan portal (izin ister)", not pi.use_mutter())


class FakeDC:
    def GetCurrentState(self):
        mode = lambda w, h, cur: ("m", w, h, 60.0, 1.0, [1.0], {"is-current": cur})  # noqa: E731
        physical = [(("DP-1", "v", "p", "s"), [mode(3840, 2160, True), mode(1920, 1080, False)], {}),
                    (("DP-2", "v", "p", "s"), [mode(1920, 1080, True)], {})]
        logical = [(0, 0, 2.0, 0, True, [("DP-1", "v", "p", "s")], {}),
                   (1920, 0, 1.0, 0, False, [("DP-2", "v", "p", "s")], {})]
        return 1, physical, logical, {}


class FakeBus:
    def get_object(self, *a):
        return object()


class FakeDbus:
    @staticmethod
    def Interface(_obj, _name):
        return FakeDC()


probe = type("P", (), {"dbus": FakeDbus, "bus": FakeBus()})()
mons = pi.MutterSession._monitors(probe)
check("Mutter monitörleri: ölçekli mantıksal boyut", mons == [
    {"connector": "DP-1", "x": 0, "y": 0, "w": 1920, "h": 1080},
    {"connector": "DP-2", "x": 1920, "y": 0, "w": 1920, "h": 1080}], str(mons))

from nexremote.platforms import linux  # noqa: E402

with mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME", "XDG_SESSION_TYPE": "wayland",
                                  "WAYLAND_DISPLAY": "w0"}):
    os.environ.pop("DISPLAY", None)
    d = linux.LinuxDesktop()
    with mock.patch.object(shutil, "which", return_value=None):
        cap = d._shot_cap()
        check("GNOME araçsız: portal Screenshot yedeği bildirilir",
              cap.available and "portal" in cap.detail.lower(), cap.detail)

bad = results.count(False)
print(f"GNOME-MANTIK: {len(results) - bad} geçti, {bad} başarısız")
sys.exit(1 if bad else 0)
