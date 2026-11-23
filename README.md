# Monti

Dikey konuşma videolarını kurgulayan küçük bir kurgucu. Kurgu programı yok; her şey bedava araçlarla, komutla yapılıyor.

- **Kulak:** Whisper konuşmayı kelime kelime, saniyesiyle yazıya döker.
- **Göz:** Gemini videoyu izleyip "eee" gibi dolgu seslerini bulur (isteğe bağlı).
- **Eller:** ffmpeg sessiz yerleri ve dolguları keser, parçaları birleştirir.
- **Altyazı:** Üçer kelime, söylenen kelime sarı.
- **Basit efektler:** yakınlaştırma, sadece arka planı karartan spotlight, kafanın etrafında dönen halka,
  kaydet düğmesi ve "Link bio'da" kapanışı.
- **Ses kutusu:** sfx-kit'ten pop, ding, whoosh.
- **Defter:** `KURALLAR.md`. Her geri bildirim bir kurala dönüşür, sonraki videoda aynı hata yapılmaz.

Hikâyesi: https://iyigirisim.net/v/monti

Mac (Apple Silicon) içindir: Whisper'ın hızlı sürümü ve kişiyi arka plandan ayıran Vision, Mac'e özel.

## Kurulum

En kolayı: [kurulum dosyasını](https://iyigirisim.net/covers/monti-kurulum.md) Claude Code'a ver ve "adımları sırayla uygula" de.
Sonra bu depoyu indir ve iki küçük aracı derle:

```bash
git clone https://github.com/abdullahkaraman/monti ~/monti/monti
cd ~/monti/monti
swiftc -O tools/personmask.swift -o tools/personmask
swiftc -O tools/faces.swift -o tools/faces
```

## Kullanım

İki adım var. Arada planı sen (ya da ajanın) gözden geçirirsin.

```bash
~/monti/venv/bin/python monti.py analyze ~/Desktop/video.mp4      # yazıya döker, work/video/plan.json yazar
# plan.json'u düzenle: başlık, kesimler, efektler, kapanış (PLAN.md)
~/monti/venv/bin/python monti.py render work/video/plan.json      # bitmiş videoyu yazar
```

Türkçe dışındaki videolar için: `monti.py analyze video.mp4 --lang en`.

Kodlama ajanıyla çalışıyorsan ona önce `AGENTS.md` dosyasını okut.

## Lisans

MIT. Ses efektleri sfx-kit'ten (CC0), bu depoda değil; kurulumda ayrıca indirilir.
