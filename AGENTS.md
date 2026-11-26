# Monti ile çalışan ajan için

Sen Monti'yi kullanarak kullanıcının dikey konuşma videosunu kurguluyorsun.

## Akış
1. `KURALLAR.md`'yi oku. Oradaki her kural bu kurgu için de geçerli.
2. `python monti.py analyze VIDEO` çalıştır. `work/<ad>/plan.json` oluşur.
3. Planı gözden geçir (`PLAN.md`):
   - `words`'ü oku; takılma, tekrar eden cümle, "buraya kadar kes" gibi talimatları `cuts`'a ekle.
   - `fillers`'ı kontrol et. Sınır bir kelimeyi kesiyorsa düzelt; dolgu değilse `"skip": true` yap.
   - Yanlış yazılmış adları `replace`'e ekle.
   - Kullanıcı istemedikçe başlık, efekt ya da kapanış ekleme; eklemeden önce ona öner.
4. `python monti.py render work/<ad>/plan.json` çalıştır. Kullanıcı gelişmiş görsel efekt / kart / baş arkası metin isterse `fx/README.md`'yi oku ve `python fx/build.py work/<ad>/plan.json OUT.mp4` kullan (önce `--preview` ile tek kare kontrol et).
5. Çıktıdan kare al ve kontrol et (`KURALLAR.md` → Kontrol). Ne yaptığını, nerede emin olmadığını kullanıcıya söyle.
6. Kullanıcının geri bildirimini uygula. Tekrar edebilecek bir hatayı `KURALLAR.md`'ye tek satırlık kural olarak ekle.

## Sınırlar
- Kaynak videonun üstüne yazma; çıktı her zaman yeni bir dosya.
- Gemini anahtarını hiçbir dosyaya yazma. Anahtar işletim sisteminin şifre kasasından (`keyring`, servis `monti`,
  hesap `gemini-api-key`) ya da `GEMINI_API_KEY`'den okunur.
- Bir adım hata verirse uydurma bir çözümle geçme; hatayı ve denediğini kullanıcıya söyle.
