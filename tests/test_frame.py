#!/usr/bin/env python3
"""Ekran yayınından kare (FRAME) — protokol ve görüntü çözümü. Gerçek
PipeWire/portal gerektirmez; sahte servis ve sahte yakalayıcı kullanır."""
import json
import os
import sys
import tempfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core"))

from computer_use_linux import portal_input as pi  # noqa: E402

results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok))
    print(("  ✓ " if ok else "  ✗ ") + name + (f" — {detail}" if detail else ""))


W, H, STRIDE = 4, 2, 20          # satır sonunda 4 bayt dolgu
# BGRx: piksel (0,0) kırmızı, (1,0) yeşil, (0,1) mavi
frame = bytearray(STRIDE * H)
frame[0:4] = bytes([0, 0, 255, 0])
frame[4:8] = bytes([0, 255, 0, 0])
frame[STRIDE:STRIDE + 4] = bytes([255, 0, 0, 0])


class FakeGrab:
    def frame(self, path, crop=None, stream=None):
        data, w, h, stride = bytes(frame), W, H, STRIDE
        cx = cy = 0
        if crop is not None:
            data, w, h, stride, cx, cy = pi.crop_raw(data, W, H, STRIDE, crop, stream)
        with open(path, "wb") as f:
            f.write(data)
        if crop is not None:
            return w, h, stride, "BGRA", cx, cy, W, H
        return w, h, stride, "BGRA"

    def stop(self):
        pass


class FakePortal:
    streams = [{"node": 1, "x": 100, "y": 0, "w": 2, "h": 1}]   # HiDPI: 2x
    devices = 3


with tempfile.TemporaryDirectory() as tmp:
    d = pi.Daemon.__new__(pi.Daemon)
    d.p, d.last, d.grab = FakePortal(), (0.0, 0.0), FakeGrab()
    raw = os.path.join(tmp, "f.raw")
    reply = d.handle("FRAME " + json.dumps(raw))
    check("FRAME yanıtı boyut + adım + mod + ekran", reply == f"OK {W} {H} {STRIDE} BGRA 100 0 2 1", reply)
    try:
        d.handle("FRAME " + json.dumps("göreli.raw"))
        check("göreli yol reddedilir", False)
    except ValueError:
        check("göreli yol reddedilir", True)

    with mock.patch.object(pi, "RUNTIME", tmp), \
            mock.patch.object(pi, "running", lambda: True), \
            mock.patch.object(pi, "send", lambda line: d.handle(line)):
        img, origin, scale = pi.frame_image()
    px = [img.getpixel((0, 0)), img.getpixel((1, 0)), img.getpixel((0, 1))]
    check("renkler doğru (BGRx → RGB, dolgu atlanır)",
          px == [(255, 0, 0), (0, 255, 0), (0, 0, 255)] and img.size == (W, H), str(px))
    check("ekran orijini ve HiDPI ölçeği", origin == (100, 0) and scale == 2.0, f"{origin} {scale}")
    check("ham dosya silinir", not os.path.exists(os.path.join(tmp, "computer-use-linux-frame.raw")))

    def _down(line):
        raise FileNotFoundError(pi.SOCK)

    with mock.patch.object(pi, "running", lambda: False), \
            mock.patch.object(pi, "send", _down), \
            mock.patch.object(pi, "_load_token", lambda: None), \
            mock.patch.object(pi, "ensure", lambda **k: (_ for _ in ()).throw(AssertionError)):
        try:
            pi.frame_image()
            check("servis+izin yoksa diyalog açmaz", False)
        except RuntimeError:
            check("servis+izin yoksa diyalog açmaz", True)

# ------------------------------------------------- servis tarafında kırpma
with tempfile.TemporaryDirectory() as tmp:
    d = pi.Daemon.__new__(pi.Daemon)
    d.p, d.last, d.grab = FakePortal(), (0.0, 0.0), FakeGrab()
    raw = os.path.join(tmp, "f.raw")
    # mantıksal (100.5, 0) 0.5x1 → yayın pikseli: x 1, y 0..2 (HiDPI 2x)
    reply = d.handle("FRAME " + json.dumps(raw) + " 100.5 0 0.5 1")
    check("FRAME kırpma: yalnızca dikdörtgen yazılır, yanıtta kırpma orijini + tam boyut",
          reply == "OK 1 2 4 BGRA 100 0 2 1 1 0 4 2", reply)
    check("kırpılmış dosya yalnızca pencerenin baytları", os.path.getsize(raw) == 8)
    with mock.patch.object(pi, "RUNTIME", tmp), \
            mock.patch.object(pi, "send", lambda line: d.handle(line)):
        img, origin, scale = pi.frame_image(crop=(100.5, 0, 0.5, 1))
    check("kırpılmış kare: piksel + orijin + ölçek",
          img.size == (1, 2) and img.getpixel((0, 0)) == (0, 255, 0) and origin == (100, 0)
          and scale == 2.0, f"{img.size} {img.getpixel((0, 0))} {origin} {scale}")
    try:
        pi.crop_raw(bytes(frame), W, H, STRIDE, (500, 500, 10, 10), FakePortal.streams[0])
        check("ekran dışı kırpma → ValueError", False)
    except ValueError:
        check("ekran dışı kırpma → ValueError", True)
    # eski servis kırpmayı bilmez: 8 alanlı yanıt → tam kare, çağıran kırpar
    old = lambda line: d.handle(line.split(" 100")[0]) if " 100" in line else d.handle(line)  # noqa: E731
    with mock.patch.object(pi, "RUNTIME", tmp), mock.patch.object(pi, "send", old):
        img, origin, scale = pi.frame_image(crop=(100.5, 0, 0.5, 1))
    check("eski servis: tam kare döner (geriye uyum)", img.size == (W, H) and origin == (100, 0))

# ------------------------------------------------- çoklu ekran (her ekran ayrı yayın)
# Sol ekran 2x1 mantıksal, sağdaki 3x2 (dikey hizasız). Her ekranın karesi tek
# renk: sol kırmızı, sağ yeşil. Ölçek 1.
class MultiPortal:
    streams = [{"node": 10, "x": 0, "y": 0, "w": 2, "h": 1},
               {"node": 11, "x": 2, "y": 0, "w": 3, "h": 2}]
    devices = 3


class MultiGrab:
    COLORS = {10: bytes([0, 0, 255, 0]), 11: bytes([0, 255, 0, 0])}
    calls: list = []

    def frame(self, path, crop=None, stream=None):
        st = stream or MultiPortal.streams[0]
        self.calls.append(st["node"])
        w, h = st["w"], st["h"]
        data = self.COLORS[st["node"]] * (w * h)
        stride = w * 4
        cx = cy = 0
        if crop is not None:
            data, w2, h2, stride, cx, cy = pi.crop_raw(data, w, h, stride, crop, st)
            with open(path, "wb") as f:
                f.write(data)
            return w2, h2, stride, "BGRA", cx, cy, w, h
        with open(path, "wb") as f:
            f.write(data)
        return w, h, stride, "BGRA"

    def stop(self):
        pass


with tempfile.TemporaryDirectory() as tmp:
    d = pi.Daemon.__new__(pi.Daemon)
    d.p, d.last, d.grab = MultiPortal(), (0.0, 0.0), MultiGrab()
    with mock.patch.object(pi, "RUNTIME", tmp), \
            mock.patch.object(pi, "running", lambda: True), \
            mock.patch.object(pi, "send", lambda line: d.handle(line)):
        MultiGrab.calls = []
        img, origin, scale = pi.frame_image()
        check("çoklu ekran: tüm masaüstü birleştirilir",
              img.size == (5, 2) and origin == (0, 0) and scale == 1.0
              and img.getpixel((0, 0)) == (255, 0, 0) and img.getpixel((4, 1)) == (0, 255, 0)
              and img.getpixel((0, 1)) == (0, 0, 0) and sorted(MultiGrab.calls) == [10, 11],
              f"{img.size} {origin} {img.getpixel((0, 0))} {img.getpixel((4, 1))} {MultiGrab.calls}")
        MultiGrab.calls = []
        img, origin, scale = pi.frame_image(crop=(3, 1, 2, 1))
        check("çoklu ekran: tek ekrandaki bölge tek istekle gelir",
              img.size == (2, 1) and origin == (3, 1) and MultiGrab.calls == [11]
              and img.getpixel((0, 0)) == (0, 255, 0), f"{img.size} {origin} {MultiGrab.calls}")
        MultiGrab.calls = []
        img, origin, scale = pi.frame_image(crop=(1, 0, 2, 1))
        check("çoklu ekran: iki ekrana yayılan bölge birleştirilir",
              img.size == (2, 1) and origin == (1, 0)
              and img.getpixel((0, 0)) == (255, 0, 0) and img.getpixel((1, 0)) == (0, 255, 0),
              f"{img.size} {origin} {[img.getpixel((i, 0)) for i in range(img.width)]}")
        try:
            pi.frame_image(crop=(50, 50, 1, 1))
            check("çoklu ekran: ekran dışı bölge → ValueError", False)
        except ValueError:
            check("çoklu ekran: ekran dışı bölge → ValueError", True)
    try:
        pi.pick_stream(MultiPortal.streams, None)
        check("pick_stream: çoklu ekranda kırpmasız istek reddedilir", False)
    except ValueError:
        check("pick_stream: çoklu ekranda kırpmasız istek reddedilir", True)

ok = sum(1 for _, o in results if o)
print(f"KARE: {ok} geçti, {len(results) - ok} başarısız")
sys.exit(0 if ok == len(results) else 1)
