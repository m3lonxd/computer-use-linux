# 3D hero: kaldığı yer (2026-11-19)

- Render sürüyor: `~/.cache/cul-medya/3d/kare3` (taban + 32 tuş × 6 kare; koyu kasa, eski ışıklar, arka plan 3. Higgsfield denemesi).
- Bitince:
  1. `cd site && python3 src/3d/kareler.py ~/.cache/cul-medya/3d/kare3 && python3 src/build.py`
     (FRAMES varsayılanı 17,33,50,67,83,100; site.js 16 ms'de bir kare oynatır.)
  2. Kontrol: hero görünümü, basış, masaüstü ve mobil.
  3. `git rm -r --cached` gereksiz yok; `site/media/keys3d` eski 2 karelik dosyaları kareler.py yazmadan önce sil: `rm site/media/keys3d/*.webp`.
- Sonra (kullanıcı onaylı): GitHub deposunu `computer-use-linux` olarak yeniden adlandır, `feat/computer-use-linux`'u master'a al ve push et, Vercel'de computeruselinux.vercel.app'e yayınla.
- Açık soru: kullanıcı "E'nin gölgesi 3'e yanlış vuruyor" dedi; ışıklar eski hâlinde, ne istendiği henüz net değil.
