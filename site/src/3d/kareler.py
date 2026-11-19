"""3D renderlarından site varlıklarını üretir.

Girdi: <kare>/taban.png ve <kare>/<tuş>_<yüzde>.png (Blender, şeffaf zemin),
       <kare>/dokum.json (tuşların ekran şekilleri), media/hero-foto.jpg (orijinal fotoğraf).
Çıktı: media/hero.{jpg,webp} (fotoğraf + 3D klavye), media/keys3d/<slug>_<yüzde>.webp
       (yalnız taban görselden farklı pikseller, yumuşak kenarlı), src/3d/tuslar.json
       (site.js'e gömülecek: tuş başına üst yüz, algılama bölgesi, kare kutusu).
Kullanım: python3 kareler.py <kare_klasörü>
"""
import hashlib, json, os, re, sys
import numpy as np
from PIL import Image, ImageFilter

SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KARE = sys.argv[1]
W, H = 1920, 1080
GRAIN = 2.0  # fotoğrafın greniyle karışsın diye 3D katmana hafif gren
# basış kareleri (TRAVEL yüzdesi); sahne.py --fracs ile aynı olmalı
FRAMES = [int(x) for x in os.environ.get("FRAMES", "17,33,50,67,83,100").split(",")]


def hull(P):
    P = sorted(set(map(tuple, P)))
    if len(P) < 3:
        return P
    def cr(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) > 1 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) > 1 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def over(base, layer, seed):
    """layer (RGBA) fotoğrafın üstüne; 3D piksellerine hafif gren."""
    a = np.asarray(layer).astype(np.float32)
    g = np.random.default_rng(seed).normal(0, GRAIN, a.shape[:2])[..., None]
    a[..., :3] = np.clip(a[..., :3] + g, 0, 255)
    out = base.copy()
    out.alpha_composite(Image.fromarray(a.astype(np.uint8), "RGBA"))
    return out


foto = Image.open(os.path.join(SITE, "media", "hero-foto.jpg")).convert("RGBA")
assert foto.size == (W, H), foto.size
taban = Image.open(os.path.join(KARE, "taban.png")).convert("RGBA")
hero = over(foto, taban, 1)
hero.convert("RGB").save(os.path.join(SITE, "media", "hero.jpg"), quality=88, optimize=True, progressive=True)
hero.convert("RGB").save(os.path.join(SITE, "media", "hero.webp"), quality=86, method=6)
HA = np.asarray(hero.convert("RGB")).astype(np.float32)

DK = json.load(open(os.path.join(KARE, "dokum.json")))
os.makedirs(os.path.join(SITE, "media", "keys3d"), exist_ok=True)
SLUG = {"~": "tilde", "Esc": "esc", "Tab": "tab", "Caps": "caps"}
out = {}
for n, v in DK.items():
    fr = {f: os.path.join(KARE, "%s_%d.png" % (n, f)) for f in FRAMES}
    if not all(os.path.exists(p) for p in fr.values()):
        continue
    comp = {f: np.asarray(over(foto, Image.open(p).convert("RGBA"), 1).convert("RGB")).astype(np.float32) for f, p in fr.items()}
    # taban görselden anlamlı fark: iki karenin birleşimi; yumuşak kenarlı maske
    d = np.max([np.abs(comp[f] - HA).mean(2) for f in FRAMES], axis=0)
    # yalnız Blender'ın render ettiği bölge (tuş şekli + 48 px, sahne.py --batch ile aynı) karşılaştırılır;
    # bölge dışı şeffaf kaldığından fotoğrafı gösterir ve fark sayılmamalı
    xs_, ys_ = [p[0] for p in v["all"]], [p[1] for p in v["all"]]
    bx0, by0 = max(0, int(min(xs_) - 46)), max(0, int(min(ys_) - 46))
    bx1, by1 = min(W, int(max(xs_) + 46)), min(H, int(max(ys_) + 46))
    reg = np.zeros_like(d); reg[by0:by1, bx0:bx1] = 1
    # ...ve tuşun kendi silüetinin 30 px çevresi: bölge kenarındaki gürültü farkı alınmaz
    from PIL import ImageDraw
    sil = Image.new("L", (W, H)); ImageDraw.Draw(sil).polygon(hull([tuple(p) for p in v["all"]]), fill=255)
    sil = np.asarray(sil.filter(ImageFilter.MaxFilter(61))) > 0
    d = d * reg * sil
    m = Image.fromarray(((d > 5) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(3))
    ma = np.asarray(m)
    ys, xs = np.nonzero(ma > 4)
    if len(xs) == 0:
        print(n, "fark yok, atlandı"); continue
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    slug = SLUG.get(n, n.lower())
    hv = hashlib.sha256()
    for f in FRAMES:
        im = Image.fromarray(comp[f].astype(np.uint8)).crop((x0, y0, x1, y1)).convert("RGBA")
        im.putalpha(m.crop((x0, y0, x1, y1)))
        fp = os.path.join(SITE, "media", "keys3d", "%s_%d.webp" % (slug, f))
        im.save(fp, quality=86, method=6); hv.update(open(fp, "rb").read())
    top = hull([tuple(p) for p in v["top"]])
    hit = hull([tuple(p) for p in v["all"]])
    out[n] = {"f": slug, "v": hv.hexdigest()[:8], "k": FRAMES, "b": [x0, y0, x1 - x0, y1 - y0],
              "t": [round(c) for p in top for c in p], "h": [round(c) for p in hit for c in p]}
    print("%-5s kare %dx%d" % (n, x1 - x0, y1 - y0))
json.dump(out, open(os.path.join(os.path.dirname(__file__), "tuslar.json"), "w"), separators=(",", ":"))
# site.js'e göm
js = os.path.join(SITE, "assets", "site.js"); t = open(js, encoding="utf-8").read()
t2, k = re.subn(r"var TUSLAR = \{.*?\};", "var TUSLAR = " + json.dumps(out, separators=(",", ":"), ensure_ascii=False) + ";", t, count=1, flags=re.S)
assert k == 1, "site.js içinde TUSLAR bulunamadı"
open(js, "w", encoding="utf-8").write(t2)
print("tuş:", len(out))
