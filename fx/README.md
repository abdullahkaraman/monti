# MontiFX (`fx/`)

Monti'nin opsiyonel görsel efekt motoru. Kesilmiş konuşma videosunun üstüne HTML/CSS ile çizilen şeffaf efektler, baş arkası metin, renk geçişleri (karanlık, sıcak, eski kamera/VCR), komut kutusu ve atölye kartları ekler.

**Sıfır npm paketi:** `render.mjs`, bilgisayarındaki Google Chrome (veya Windows'ta Edge) ile Node 22+ yerleşik `WebSocket`'i üzerinden kare kare şeffaf katman üretir, `build.py` bunu FFmpeg ile videoya bindirir.

## Gereksinimler (Monti'ye ek)

- **Node.js 22+** (`node --version`)
- **Google Chrome** (veya Windows'ta Edge; özel yol için `CHROME=/yol/chrome`)

## Kullanım

1. Önce standart Monti analiziyle zaman çizelgesini çıkar:

```bash
python monti.py analyze video.mp4
```

2. `work/video/plan.json` içine `"kit": { ... }` bloğunu ekle (örnek: `fx/ornek/dergi_deneme1.kit.json`). Zamanlar **kaynak video saniyesi** cinsindendir; `build.py` kesimlere göre otomatik kaydırır.

3. Önce tek kare önizleme al (hızlı):

```bash
python fx/build.py work/video/plan.json out.mp4 --preview 1.0 5.5
```

4. Beğendiğinde tam videoyu üret:

```bash
python fx/build.py work/video/plan.json out.mp4
```

## Parçalar (`plan["kit"]["ui"]`)

| type | ne yapar |
|---|---|
| `lockup` | büyüklü küçüklü katmanlı başlık |
| `tags` | söyledikçe gelen kâğıt etiketler, çizilir/tiklenir, düşer |
| `label` | tek etiket; üstü çizilir, altına el yazısı gelir |
| `art` | çizim/görsel, çizilerek girer (`fx/assets/*.png`) |
| `flow` | sıra sıra yanan ve tiklenen adımlar |
| `strip` | ses şeridi; makas çöp parçayı keser, şerit kapanır |
| `note` | defter sayfası; söz yazılır, damga basılır |
| `raf` | kâğıt kartlar sırayla yükselir; konuşulan renklenir |
| `zaman` | akan kâğıt zaman şeridi |
| `komut` | yazılan komut kutusu |
| `fon` | kişinin arkasında renk katmanı (`"behind": true`) |
| `yazi` | harf harf yükselen baş arkası tipografi (`"behind": true`) |
| `kapak` | dergi kapağı çerçevesi (`"behind": true`) |
| `silmecizgi` | renk silmesinin parlak kenarı |
| `ses` | tek başına ses efekti (`sfx-kit`) |

- `"behind": true` eklenen her parça kişinin arkasına çizilir (`vision.py`: Mac'te Apple Vision, Windows'ta MediaPipe).
- `looks`: `[{"at": 4.0, "end": 8.0, "style": "karanlik" | "sicak" | "vcr"}]` çapraz silmeyle renk/filtre geçişi yapar.
