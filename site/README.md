# Computer Use Linux — tanıtım sitesi

Statik site (framework yok), iki dilli: `/` (EN) ve `/tr/` (TR). Eski adı
NexRemote; komut, paket ve depo adı `nexremote` olarak kalır.

## Yapı
```
site/
├── src/
│   ├── page.html       tek şablon ({{anahtar}} yer tutucuları)
│   └── build.py        şablon + metinler (EN/TR) + README/kod sayıları -> iki HTML
├── index.html          ÜRETİLİR (EN) — elle düzenlenmez
├── tr/index.html       ÜRETİLİR (TR) — elle düzenlenmez
├── assets/
│   ├── site.css        tasarım sistemi (koyu mor zemin, turuncu vurgu; açık tema seçmeli)
│   ├── site.js         sekmeler, kopyala, kaydırma animasyonları, döngü videoları
│   └── mark.svg        favicon
├── media/              döngü videoları ve posterleri (aşağıya bak)
├── download/           üretilen indirme paketleri (nexremote.zip / .tar.gz)
├── make_download.sh    paketi yeniden üretir
└── vercel.json         başlık + yönlendirme kuralları
```

## Siteyi yeniden üret
```bash
python3 site/src/build.py
```
Sayfadaki sayılar (MCP aracı, CLI komutu, test paketi, kod satırı...) koddan
ölçülür; okunamayan sayıda derleme durur. Metinleri `build.py` içindeki `S`
sözlüğünde düzenleyin, `index.html` dosyalarını elle değiştirmeyin.

## Döngü videosu (hero ve "terminaller" bölümü)
İki bölümün arka planı tam alan `<picture>` (webp + jpg) üstünde sessiz,
döngülü `<video>`dur. Dosya sözleşmesi (EN ve TR sayfa aynı dosyaları kullanır):

| Dosya | Boyut | İçerik |
|---|---|---|
| `media/hero.webp`, `media/hero.jpg` | 1920x1072 | karanlık masa, ultra geniş monitörde soyut pencereler, parlayan AI imleci izi; sol %40 koyu (metin solda) |
| `media/hero.webm`, `media/hero.mp4` | 1280x720 | aynı sahnenin döngü videosu |
| `media/ikinci.webp`, `media/ikinci.jpg` | 1920x1072 | havada süzülen holografik terminal pencereleri |
| `media/ikinci.webm`, `media/ikinci.mp4` | 1280x720 | aynı sahnenin döngü videosu |

Davranış (`site.js`): `prefers-reduced-motion` veya `navigator.connection.saveData`
varsa video kaldırılır, poster kalır; ekran dışındaki video durur
(IntersectionObserver); ikinci video görünür olana dek yüklenmez (`data-gec`);
`play()` `NotAllowedError` verirse video kaldırılır, `AbortError`'da bir sonraki
görünüşte yeniden denenir. Okunabilirlik için videoların üstünde koyu gradyan var.
Medya dosyaları depoya sonradan eklenir; eksikken poster/video yüklenmez, metin
okunur kalır.

## İndirme paketini güncelle
Proje kodu değiştiğinde:
```bash
bash site/make_download.sh      # depo kökünden çalıştır
```

## Yerel önizleme
```bash
cd site && python3 -m http.server 8899 --bind 127.0.0.1     # http://127.0.0.1:8899
```

## Deploy
Bu çalışmada deploy edilmedi. Yayınlamak için (kullanıcı onayıyla):
```bash
cd site && vercel --prod
```
