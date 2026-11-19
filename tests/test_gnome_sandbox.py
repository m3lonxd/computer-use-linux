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

if os.environ.get("NEXR_GNOME") != "1":
    sys.exit("bu test yalnızca tests/gnome_sandbox.sh içinde çalışır (gerçek masaüstüne dokunmaz)")

ENV = {**os.environ, "PYTHONPATH": f"{ROOT}/core:{ROOT}/adapters/cli", "NEXREMOTE_CURSOR": "0"}
LOG = os.path.join(os.environ["XDG_RUNTIME_DIR"], "probe.jsonl")
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail else ""), flush=True)


def skip(name: str, why: str) -> None:
    print(f"  ⊘ {name} — atlandı: {why}", flush=True)


def nx(*args: str, timeout: float = 40) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, f"{ROOT}/adapters/cli/nexremote_cli.py", *args],
                          capture_output=True, text=True, timeout=timeout, env=ENV)


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
        from nexremote.platforms.linux import session_kind
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
              any("nexremote-probe" in (w.get("title") or "") for w in wl),
              (ws.stderr.strip() or f"{len(wl)} pencere")[:100])

        found = nx("find", "probe-entry", "--json")
        check("find: AT-SPI ile ada göre öğe bulma",
              found.returncode == 0 and "probe" in found.stdout.lower(), found.stderr.strip()[:80])

        # --- portal girişi: izin diyaloğu onaylanmazsa atla
        n = len(events())
        r = nx("click", "640", "400", timeout=60)
        hit = wait_for(lambda: since(n, "button"), 5)
        if r.returncode != 0 and not hit:
            skip("portal ile fare/klavye", "RemoteDesktop izin diyaloğu başsızda onaylanamadı: "
                 + (r.stderr.strip() or r.stdout.strip())[:120])
        else:
            check("sol tık doğru koordinatta", bool(hit) and hit[0]["button"] == 1
                  and abs(hit[0]["x"] - 640) <= 2 and abs(hit[0]["y"] - 400) <= 2,
                  str(hit[0] if hit else ""))
            nx("click", "640", "12")
            time.sleep(0.2)
            text = "Merhaba dünya ğüşıöç"
            r = nx("type", text)
            got = wait_for(lambda: [e for e in since(0, "text") if e["value"] == text], 8)
            check("portal ile Türkçe yazı", r.returncode == 0 and bool(got),
                  (since(0, "text") or [{}])[-1].get("value", r.stderr.strip()))
            n = len(events())
            nx("key", "ctrl+a")
            check("tuş kombinasyonu ctrl+a",
                  bool(wait_for(lambda: [e for e in since(n, "key") if e["name"] == "a" and e["ctrl"]])))

        shot = os.path.join(os.environ["XDG_RUNTIME_DIR"], "s.png")
        r = nx("screenshot", shot, "--json")
        try:
            info = json.loads(r.stdout)
        except ValueError:
            info = {}
        if r.returncode != 0 or not os.path.exists(shot):
            skip("ekran görüntüsü", (r.stderr.strip() or "araç yok / portal onayı yok")[:120])
        else:
            check("ekran görüntüsü alındı", os.path.getsize(shot) > 1000,
                  f"{info.get('backend')} {info.get('width')}x{info.get('height')}")
    finally:
        if probe.poll() is None:
            probe.terminate()
            probe.wait(5)

    bad = [n for n, ok, _ in results if not ok]
    print(f"GNOME: {len(results) - len(bad)} geçti, {len(bad)} başarısız")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
