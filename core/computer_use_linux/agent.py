"""Ajan kimliği: aynı masaüstünde paralel çalışan ajanları ayırır.

Kimlik `CUL_AGENT` ortam değişkeninden (CLI'da `--agent AD`) gelir. Kimlik
varsa her ajanın:
    - kendi yardımcı servisi (biri `wait`/`do` ile beklerken diğeri durmaz),
    - kendi görünür imleci (ayrı süreç, ayrı renk),
    - kendi son ekran görüntüsü kaydı (`--from-shot` başkasının görüntüsüne
      göre tıklamaz),
    - kendi varsayılan terminal oturumu
olur. Fare/klavye gönderimi makine genelinde tek kilitle (lease) sıralanır:
gerçek imleç tek, olaylar birbirine karışmasın.

Kimlik yoksa davranış tek ajanlı eski davranışın aynısıdır.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

# Varsayılan (kimliksiz) imleç yeşil; ajanlara yeşilden ayırt edilen renkler.
DEFAULT_COLOR = (0x6e, 0xe7, 0xa8)
PALETTE = (
    (0xff, 0xa9, 0x4d),   # turuncu
    (0x6c, 0xb6, 0xff),   # mavi
    (0xff, 0x7a, 0xc6),   # pembe
    (0xf5, 0xe1, 0x4b),   # sarı
    (0xb1, 0x8c, 0xff),   # mor
    (0x4d, 0xe0, 0xe6),   # camgöbeği
    (0xff, 0x6b, 0x6b),   # kırmızı
    (0xc8, 0xf0, 0x6e),   # açık yeşil
)
SLOT_TTL = 3600.0         # bu kadar süre görülmeyen ajanın renk yuvası boşalır

# Ajan imleçleri Material Bibata temalarından (kuruluysa): her ajan ayrı renk
# varyantı. Sıra, yan yana en kolay ayırt edilen renklerden başlar.
MATERIAL = ("Sunset", "Sky-Blue", "Pink-Rose", "Lime", "Violet", "Teal", "Salmon",
            "Deep-Blue", "Mint", "Apricot", "Lilac", "Moss", "Peach", "Seafoam",
            "Soft-Blue", "Blush", "Sage", "Sand", "Ice-Blue", "Brown", "Pink-Pastel",
            "Grey", "Charcoal", "Midnight", "Noir", "Cloud", "Beige", "Slate")
_themes_cache: Optional[list[str]] = None


def themes() -> list[str]:
    """Kurulu Material Bibata temaları (MATERIAL sırasıyla); kullanıcının kendi
    imleç teması hariç — ajan imleci gerçek imleçle karışmasın. Yoksa []."""
    global _themes_cache
    if _themes_cache is None:
        try:
            from .cursor_theme import _theme_dirs, theme_and_size
            own = (theme_and_size()[0] or "").lower()
            _themes_cache = [f"Bibata-Material-{m}" for m in MATERIAL
                             if f"bibata-material-{m}".lower() != own
                             and _theme_dirs(f"Bibata-Material-{m}")]
        except Exception:
            _themes_cache = []
    return _themes_cache


def _slot_count() -> int:
    return len(themes()) or len(PALETTE)

_NAME = re.compile(r"[^a-z0-9_-]+")
_TR = str.maketrans("ıİşŞğĞüÜöÖçÇâÂîÎûÛ", "iissgguuooccaaiiuu")


def clean(name: str) -> str:
    """Dosya adına ve sokete güvenli kısa ad: [a-z0-9_-], en fazla 24 karakter.
    Türkçe harfler ASCII karşılığına çevrilir (Kırmızı → kirmizi)."""
    return _NAME.sub("-", (name or "").strip().translate(_TR).lower()).strip("-")[:24]


def agent_id() -> str:
    """Geçerli ajan kimliği; yoksa ""."""
    return clean(os.environ.get("CUL_AGENT", ""))


def suffix() -> str:
    """Dosya/soket adı eki: kimlik yoksa "" (eski adlar aynen kalır)."""
    a = agent_id()
    return f"-{a}" if a else ""


def _runtime() -> str:
    from .platforms.base import runtime_dir
    return os.environ.get("CUL_HOME") or runtime_dir()


def _slots_path() -> str:
    return os.path.join(_runtime(), "computer-use-linux-agents.json")


def slot(name: Optional[str] = None) -> int:
    """Ajanın renk yuvası (0..yuva sayısı-1; tema varsa tema sayısı). İlk gelen ilk boş yuvayı alır;
    aynı anda çalışan ajanlar böylece farklı renk görür (karma değil, çakışma
    yok). Kayıt dosyası kilitle korunur; okunamazsa ada göre karmaya düşer."""
    name = clean(name if name is not None else agent_id())
    if not name:
        return -1
    path = _slots_path()
    try:
        import fcntl
        fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                with open(path) as f:
                    reg = json.load(f)
                if not isinstance(reg, dict):
                    reg = {}
            except (OSError, ValueError):
                reg = {}
            now = time.time()
            reg = {k: v for k, v in reg.items()
                   if isinstance(v, dict) and now - float(v.get("seen", 0)) < SLOT_TTL}
            if name in reg:
                s = int(reg[name]["slot"]) % _slot_count()
            else:
                used = {int(v.get("slot", -1)) for v in reg.values()}
                s = next((i for i in range(_slot_count()) if i not in used),
                         len(reg) % _slot_count())
            reg[name] = {"slot": s, "seen": now}
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(reg, f)
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
            return s
        finally:
            os.close(fd)
    except (OSError, ImportError, ValueError):
        import zlib
        return zlib.crc32(name.encode()) % _slot_count()


def color(name: Optional[str] = None) -> tuple[int, int, int]:
    """Yerleşik ok rengi (tema bulunamazsa); kimlik yoksa varsayılan yeşil."""
    s = slot(name)
    return DEFAULT_COLOR if s < 0 else PALETTE[s % len(PALETTE)]


def theme(name: Optional[str] = None) -> Optional[str]:
    """Ajanın Material Bibata imleç teması; kimlik ya da tema yoksa None."""
    s = slot(name)
    ts = themes()
    return ts[s % len(ts)] if s >= 0 and ts else None
