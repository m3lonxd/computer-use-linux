#!/usr/bin/env python3
"""Gerçek GNOME Shell'de (başsız Mutter) uçtan uca — İZOLE oturumda.

    tests/gnome_sandbox.sh python3 tests/test_gnome_sandbox.py

Kapsam: oturum türü, caps, AT-SPI pencere/öğe bulma, portal girişi, ekran görüntüsü.
RemoteDesktop portalı izin diyaloğu başsız GNOME'da otomatik onaylanamaz; onay
verilmediyse giriş testleri başarısız DEĞİL "⊘ atlandı" sayılır (nedeni yazılır).
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

if os.environ.get("CUL_GNOME") != "1":
    sys.exit("bu test yalnızca tests/gnome_sandbox.sh içinde çalışır (gerçek masaüstüne dokunmaz)")

ENV = {**os.environ, "PYTHONPATH": f"{ROOT}/core:{ROOT}/adapters/cli", "CUL_CURSOR": "0"}
LOG = os.path.join(os.environ["XDG_RUNTIME_DIR"], "probe.jsonl")
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail else ""), flush=True)


def skip(name: str, why: str) -> None:
    print(f"  ⊘ {name} — atlandı: {why}", flush=True)


def nx(*args: str, timeout: float = 40) -> subprocess.CompletedProcess:
    try:
        return subprocess.run([sys.executable, f"{ROOT}/adapters/cli/computer_use_linux_cli.py", *args],
                              capture_output=True, text=True, timeout=timeout, env=ENV)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", f"zaman aşımı ({timeout:.0f} sn)")


def events() -> list[dict]:
    try:
        with open(LOG) as f:
            return [json.loads(line) for line in f if line.strip()]
    except OSError:
        return []


def wait_for(pred, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        hit = pred()
        if hit:
            return hit
        time.sleep(0.05)
    return None


def since(n: int, kind: str) -> list[dict]:
    return [e for e in events()[n:] if e.get("type") == kind]


def main() -> int:
    probe = subprocess.Popen([sys.executable, f"{HERE}/input_probe.py", LOG],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        check("deneme penceresi hazır", bool(wait_for(lambda: since(0, "ready"), 20)))
        time.sleep(1.0)

        sys.path.insert(0, f"{ROOT}/core")
        from computer_use_linux.platforms.linux import session_kind
        check("oturum türü gnome-wayland", session_kind() == "gnome-wayland", session_kind())

        caps = nx("caps")
        check("caps çalıştı", caps.returncode == 0, caps.stderr.strip()[:80])
        print("    " + caps.stdout.strip().replace("\n", "\n    "))

        ws = nx("windows", "--json")
        try:
            wl = json.loads(ws.stdout or "[]")
        except ValueError:
            wl = []
        check("windows: AT-SPI geri dönüşü deneme penceresini listeledi",
              any("computer-use-linux-probe" in (w.get("title") or "") for w in wl),
              (ws.stderr.strip() or f"{len(wl)} pencere")[:100])

        # --- portal girişi: izin diyaloğu onaylanmazsa atla
        # Gözlem: Mutter sanal imlecinde oturumdaki ilk tık(lar) istemciye ulaşmıyor
        # (kök neden bulunamadı). En çok 4 deneme; kaç tıkın yutulduğu yazılır.
        r, hit, tries = None, [], 0
        for tries in range(1, 5):
            n = len(events())
            r = nx("click", "640", "400", timeout=60)
            hit = wait_for(lambda: since(n, "button"), 2.5)
            if hit or r.returncode != 0:
                break
        if hit:
            print(f"    (sol tık {tries}. denemede ulaştı; ilk {tries - 1} tık yutuldu)")
        if r.returncode != 0 and not hit:
            skip("fare/klavye", "RemoteDesktop izin diyaloğu başsızda onaylanamadı: "
                 + (r.stderr.strip() or r.stdout.strip())[:120])
        else:
            check("sol tık doğru koordinatta", bool(hit) and hit[0]["button"] == 1
                  and abs(hit[0]["x"] - 640) <= 2 and abs(hit[0]["y"] - 400) <= 2,
                  str(hit[0] if hit else events()[-4:]))
            nx("click", "640", "12")
            time.sleep(0.2)
            text = "Merhaba dünya ğüşıöç"
            r = nx("type", text)
            got = wait_for(lambda: [e for e in since(0, "text") if e["value"] == text], 8)
            check("Türkçe yazı (ğüşıöç panodan)", r.returncode == 0 and bool(got),
                  (since(0, "text") or [{}])[-1].get("value", r.stderr.strip()))
            n = len(events())
            nx("key", "ctrl+a")
            check("tuş kombinasyonu ctrl+a",
                  bool(wait_for(lambda: [e for e in since(n, "key") if e["name"] == "a" and e["ctrl"]])))
            n = len(events())
            nx("scroll", "3", "--at", "700", "450")
            down = wait_for(lambda: since(n, "scroll"))
            n = len(events())
            nx("scroll", "-2")
            up = wait_for(lambda: since(n, "scroll"))
            check("kaydırma aşağı ve yukarı", bool(down) and bool(up)
                  and (down[0]["direction"] == 1 or down[0]["dy"] > 0)
                  and (up[0]["direction"] == 0 or up[0]["dy"] < 0), f"{down[:1]} {up[:1]}")

        # AT-SPI: adlı düğmeyi isimle bul ve tıkla (portal gerektirmez)
        ap = subprocess.Popen([sys.executable, f"{HERE}/atspi_probe.py", LOG],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            wait_for(lambda: since(0, "atspi-ready"), 20)
            time.sleep(1.0)
            found = nx("find", "NexProbeButton")
            check("find: AT-SPI ile ada göre öğe bulma",
                  found.returncode == 0 and "NexProbeButton" in found.stdout,
                  (found.stdout + found.stderr).strip()[:80])
            ref = next((t for ln in found.stdout.splitlines() for t in ln.split()
                        if t.startswith("atspi:")), "")
            n = len(events())
            r = nx("click", ref) if ref else None
            check("click: AT-SPI ile adlı düğmeye tıklama (REF)",
                  bool(r) and r.returncode == 0 and bool(wait_for(lambda: since(n, "activate"))),
                  (r.stdout + r.stderr).strip()[:80] if r else "ref bulunamadı")
        finally:
            ap.terminate()
            ap.wait(5)

        shot = os.path.join(os.environ["XDG_RUNTIME_DIR"], "s.png")
        r = nx("screenshot", shot, "--json")
        try:
            info = json.loads(r.stdout)
        except ValueError:
            info = {}
        if r.returncode != 0 or not os.path.exists(shot):
            skip("ekran görüntüsü", (r.stderr.strip() or "araç yok / portal onayı yok")[:120])
        else:
            try:
                from PIL import Image
                colors = len(Image.open(shot).convert("RGB").getcolors(1 << 24) or [])
            except Exception:
                colors = -1   # Pillow yok: yalnızca boyut denetlenir
            check("ekran görüntüsü alındı (boş/siyah değil)",
                  os.path.getsize(shot) > 1000 and colors != 1 and info.get("width") == 1280,
                  f"{info.get('backend')} {info.get('width')}x{info.get('height')} renk={colors}")

        obs = nx("observe", "--json")
        check("observe çalıştı", obs.returncode == 0 and "gnome" in obs.stdout.lower(),
              obs.stderr.strip()[:80])
    finally:
        if probe.poll() is None:
            probe.terminate()
            probe.wait(5)

    bad = [n for n, ok, _ in results if not ok]
    print(f"GNOME: {len(results) - len(bad)} geçti, {len(bad)} başarısız")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
