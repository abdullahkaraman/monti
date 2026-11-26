# Monti

Dikey konuşma videolarını kurgulayan küçük bir kurgucu. Kurgu programı yok; her şey bedava araçlarla, komutla yapılıyor.

- **Kulak:** Whisper konuşmayı kelime kelime, saniyesiyle yazıya döker.
- **Göz:** Gemini videoyu izleyip "eee" gibi dolgu seslerini bulur (isteğe bağlı).
- **Eller:** ffmpeg sessiz yerleri ve dolguları keser, parçaları birleştirir.
- **Altyazı:** Üçer kelime, söylenen kelime sarı.
- **Basit efektler:** yakınlaştırma, sadece arka planı karartan spotlight, kafanın etrafında dönen halka,
  kaydet düğmesi ve "Link bio'da" kapanışı.
- **MontiFX (`fx/`, isteğe bağlı):** HTML/CSS ile çizilen şeffaf efekt kartları, baş arkası metin, renk geçişleri
  (karanlık, sıcak, eski kamera/VCR) ve atölye parçaları (`fx/README.md`). Sıfır npm paketi; Node 22+ ve Chrome/Edge ile çalışır.
- **Ses kutusu:** sfx-kit'ten pop, ding, whoosh.
- **Defter:** `KURALLAR.md`. Her geri bildirim bir kurala dönüşür, sonraki videoda aynı hata yapılmaz.

Hikâyesi: https://iyigirisim.net/v/monti

Mac (Apple Silicon) ve Windows 10/11'de çalışır. Mac'te Whisper'ın Mac çipine özel hızlı sürümünü ve kişiyi arka plandan
ayırmak için Apple Vision'ı; Windows'ta OpenAI'nin Whisper'ını ve MediaPipe'ı kullanır.

## Kurulum

En kolayı: [kurulum dosyasını](https://iyigirisim.net/covers/monti-kurulum.md) Claude Code'a ver ve "adımları sırayla uygula" de.
Dosya Monti'yi de indirir; Mac'te iki küçük aracı derler (`tools/`), Windows'ta derlenecek bir şey yok.

## Kullanım

İki adım var. Arada planı sen (ya da ajanın) gözden geçirirsin.

```bash
python monti.py analyze video.mp4          # yazıya döker, work/video/plan.json yazar
# plan.json'u düzenle: başlık, kesimler, efektler, kapanış (PLAN.md)
python monti.py render work/video/plan.json # bitmiş videoyu yazar
```

`python`, kurulumda açılan ortamınki: Mac'te `~/monti/venv/bin/python`, Windows'ta `$HOME\monti\venv\Scripts\python.exe`.

Türkçe dışındaki videolar için: `monti.py analyze video.mp4 --lang en`.

Kodlama ajanıyla çalışıyorsan ona önce `AGENTS.md` dosyasını okut.

## Lisans

MIT. Ses efektleri sfx-kit'ten (CC0), bu depoda değil; kurulumda ayrıca indirilir.
