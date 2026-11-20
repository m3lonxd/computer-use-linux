#!/usr/bin/env python3
"""Paralel ajanlar (CUL_AGENT / --agent): kimlik, renk yuvası, ajana özel
dosya ve soket adları, varsayılan terminal oturumu. Masaüstüne dokunmaz."""
import importlib
import os
import sys
import tempfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "core"))
sys.path.insert(0, os.path.join(HERE, "..", "adapters", "cli"))

results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok))
    print(("  ✓ " if ok else "  ✗ ") + name + (f" — {detail}" if detail else ""))


with tempfile.TemporaryDirectory() as home, \
        mock.patch.dict(os.environ, {"CUL_HOME": home}, clear=False):
    os.environ.pop("CUL_AGENT", None)
    from computer_use_linux import agent

    check("ad temizlenir (Türkçe harf ASCII'ye)", agent.clean("  Ajan 1/ÖZEL..x ") == "ajan-1-ozel-x",
          agent.clean("  Ajan 1/ÖZEL..x "))
    check("ad 24 karakterle sınırlı", len(agent.clean("a" * 40)) == 24)
    check("kimlik yoksa ek ve renk eskisi gibi",
          agent.suffix() == "" and agent.color() == agent.DEFAULT_COLOR and agent.slot() == -1)

    s1, s2, s3 = agent.slot("a"), agent.slot("b"), agent.slot("c")
    check("eşzamanlı ajanlar farklı renk yuvası alır", len({s1, s2, s3}) == 3, f"{s1} {s2} {s3}")
    check("aynı ajan aynı yuvayı korur", agent.slot("b") == s2)
    check("ajan rengi varsayılan yeşilden farklı",
          all(agent.color(n) != agent.DEFAULT_COLOR for n in "abc"))

    import json
    import time
    path = os.path.join(home, "computer-use-linux-agents.json")
    reg = json.load(open(path))
    reg["a"]["seen"] = time.time() - agent.SLOT_TTL - 1
    json.dump(reg, open(path, "w"))
    check("süresi geçen ajanın yuvası boşalır", agent.slot("d") == s1, str(agent.slot("d")))

    with mock.patch.dict(os.environ, {"CUL_AGENT": "Mavi Ajan"}):
        check("CUL_AGENT → kimlik ve ek", agent.agent_id() == "mavi-ajan"
              and agent.suffix() == "-mavi-ajan")
        from computer_use_linux import desktop
        check("son ekran görüntüsü kaydı ajana özel",
              desktop._shot_file("json").endswith("computer-use-linux-shot-mavi-ajan.json"),
              desktop._shot_file("json"))
        from computer_use_linux import agent_cursor
        check("imleç daemon soketi ajana özel",
              agent_cursor.sock_path().endswith("-mavi-ajan.sock"), agent_cursor.sock_path())
        ac = importlib.reload(agent_cursor)
        check("imleç daemon'ı ajan rengini kullanır",
              ac.COLOR == agent.color("mavi-ajan") and ac.PULSE == ac.COLOR, str(ac.COLOR))
    ac = importlib.reload(agent_cursor)
    check("kimliksiz imleç yeşil ve eski soket adı",
          ac.COLOR == agent.DEFAULT_COLOR and ac.sock_path().endswith(f"-{ac.PROTO}.sock"))

    import computer_use_linux_cli as cli
    with mock.patch.dict(os.environ, {}):
        os.environ.pop("CUL_AGENT", None)
        out = cli._take_agent(["--agent", "Kırmızı", "screenshot", "--screen", "all"])
        check("--agent AD bayrağı çıkarılır, CUL_AGENT yazılır",
              out == ["screenshot", "--screen", "all"] and os.environ.get("CUL_AGENT") == "kirmizi",
              f"{out} {os.environ.get('CUL_AGENT')}")
    with mock.patch.dict(os.environ, {}):
        os.environ.pop("CUL_AGENT", None)
        out = cli._take_agent(["click", "10", "20", "--agent=b2"])
        check("--agent=AD komuttan sonra da olur", out == ["click", "10", "20"]
              and os.environ.get("CUL_AGENT") == "b2")
    with mock.patch.dict(os.environ, {}):
        os.environ.pop("CUL_AGENT", None)
        out = cli._take_agent(["launch", "prog", "--agent", "x"])
        check("launch sonrası argümanlara dokunulmaz",
              out == ["launch", "prog", "--agent", "x"] and "CUL_AGENT" not in os.environ)
    with mock.patch.dict(os.environ, {"CUL_AGENT": "a1"}):
        p1 = cli._service_path()
    with mock.patch.dict(os.environ, {"CUL_AGENT": "a2"}):
        p2 = cli._service_path()
    check("her ajanın kendi yardımcı servisi", p1 != p2)

    parser = cli.build_parser()
    a = parser.parse_args(["run", "true"])
    with mock.patch.dict(os.environ, {"CUL_AGENT": "a1"}):
        cli._default_session(a)
    b = parser.parse_args(["screen"])
    os.environ.pop("CUL_AGENT", None)
    cli._default_session(b)
    c = parser.parse_args(["keys", "C-c", "--session", "build"])
    cli._default_session(c)
    check("varsayılan oturum: ajan adı / default / verilen",
          (a.session, b.session, c.session) == ("a1", "default", "build"),
          f"{a.session} {b.session} {c.session}")

# ------------------------------------------------- KWin artık izleyici temizliği
with tempfile.TemporaryDirectory() as home, \
        mock.patch.dict(os.environ, {"CUL_HOME": home}, clear=False):
    from computer_use_linux import kwin

    class FakeScripting:
        def __init__(self, loaded):
            self.loaded = set(loaded)

        def isScriptLoaded(self, name):
            return name in self.loaded

        def unloadScript(self, name):
            had = name in self.loaded
            self.loaded.discard(name)
            return had

    dead = 4194000          # pid_max sınırına yakın: çalışan süreç olamaz
    live = os.getpid()
    kwin._registry_update(add=f"cul_watch_{dead}")
    kwin._registry_update(add=f"cul_watch_{live}")
    fs = FakeScripting({f"cul_watch_{dead}", f"cul_watch_{live}", "kullanicinin_betigi"})
    removed = kwin.reap_stale(fs)
    check("ölü sürecin izleyici betiği kaldırılır, canlınınki kalır",
          removed == [f"cul_watch_{dead}"] and fs.loaded == {f"cul_watch_{live}", "kullanicinin_betigi"},
          f"{removed} {fs.loaded}")
    check("kayıt dosyası güncellenir", kwin._registry_update() == [f"cul_watch_{live}"])
    fs2 = FakeScripting({"cul_watch_3", "kullanicinin_betigi"})   # kayıtta yok: eski sürüm artığı
    with mock.patch.object(kwin, "_pid_alive", lambda pid: pid != 3):
        removed = kwin.reap_stale(fs2, scan=True)
    check("tarama kayıtsız artığı bulur, başka betiğe dokunmaz",
          removed == ["cul_watch_3"] and fs2.loaded == {"kullanicinin_betigi"}, f"{removed} {fs2.loaded}")

# ------------------------------------------------- Material Bibata imleç teması
from computer_use_linux import agent as ag2  # noqa: E402
from computer_use_linux import agent_cursor as ac2  # noqa: E402
from computer_use_linux.cursor_theme import CursorImage  # noqa: E402

with tempfile.TemporaryDirectory() as home:
    icons = os.path.join(home, "icons")
    for m in ("Sunset", "Sky-Blue", "Slate", "Teal"):
        os.makedirs(os.path.join(icons, f"Bibata-Material-{m}", "cursors"))
    import computer_use_linux.cursor_theme as ctm
    with mock.patch.object(ctm, "_theme_dirs",
                           lambda t: [os.path.join(icons, t)] if os.path.isdir(os.path.join(icons, t)) else []), \
            mock.patch.object(ctm, "theme_and_size", lambda: ("Bibata-Material-Slate", 24)), \
            mock.patch.dict(os.environ, {"CUL_HOME": home}):
        ag2._themes_cache = None
        ts = ag2.themes()
        check("kurulu Material temaları, ayırt edici sırayla, kullanıcının teması hariç",
              ts == ["Bibata-Material-Sunset", "Bibata-Material-Sky-Blue", "Bibata-Material-Teal"], str(ts))
        got = [ag2.theme(n) for n in ("x1", "x2", "x3")]
        check("her ajana ayrı tema", len(set(got)) == 3, str(got))
    ag2._themes_cache = None

    def img(pixels):
        return CursorImage(len(pixels), 1, 0, 0, b"".join(bytes(p) for p in pixels), "test")
    # BGRA: turuncu (r=255,g=140,b=40) + siyah kenar + beyaz
    a = ac2.accent(img([(40, 140, 255, 255), (0, 0, 0, 255), (255, 255, 255, 255), (40, 140, 255, 0)]))
    check("tık halkası imlecin vurgu rengini alır", a == (255, 140, 40), str(a))
    check("renksiz (gri) imleçte halka varsayılan kalır",
          ac2.accent(img([(0, 0, 0, 255), (128, 128, 128, 255)])) is None)

ok = sum(1 for _, o in results if o)
print(f"AJANLAR: {ok} geçti, {len(results) - ok} başarısız")
sys.exit(0 if ok == len(results) else 1)
