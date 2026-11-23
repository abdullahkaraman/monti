# plan.json

`monti.py analyze` yazar, sen düzenlersin, `monti.py render` okur. Bütün zamanlar **kaynak videonun saniyesi**dir;
render kesimlere göre çıktıdaki yerini kendisi bulur.

| Alan | Ne yapar |
|---|---|
| `source` | Kaynak video. |
| `range` | `[başlangıç, bitiş]`: videonun kullanılacak kısmı. |
| `words` | Whisper'ın kelimeleri ve zamanları. Altyazı bunlardan çıkar; elle düzeltilebilir. |
| `cuts` | `[[başlangıç, bitiş, "neden"], ...]` atılacak kısımlar: takılma, tekrar eden cümle, "buraya kadar kes" talimatı. |
| `fillers` | Gemini'nin bulduğu "eee"ler. Sınırı düzelt ya da tutmak için `"skip": true` ekle. |
| `max_gap` | Bundan uzun sessizlikler kesilir (saniye, varsayılan 0.35). |
| `pad` | Sessizlik kesilirken iki yanda bırakılan pay (saniye, varsayılan 0.12). |
| `protect` | `[[başlangıç, bitiş], ...]` sessiz ama kalması gereken kısımlar (bilinçli bir duraklama, kameraya giriş). |
| `replace` | `{"Klod": "Claude"}`: Whisper'ın yanlış yazdığı adlar. Ekli hâlini korur ("Klod'la" → "Claude'la"). |
| `title` | `{"lines": ["satır 1", "satır 2"], "until": 4.0}`: açılışta beyaz kutularda başlık, `until` saniyeye kadar. |
| `effects` | Aşağıdaki efektlerin listesi. |
| `outro` | `{"save_at": saniye, "hold": 2.2, "text": "Link bio'da"}` ya da `null`. |

## Efektler

Her efekt `{"type": ..., "at": saniye}` ile başlar. `"sound": null` sesini kapatır, `"sound": "ding"` değiştirir.

| type | alanlar | ne yapar | ses |
|---|---|---|---|
| `zoom` | `dur` 1.5, `scale` 1.3, `cx` 540, `cy` 760 | Yüze yakınlaşır (punch-in). Vurgulu bir cümlede. | whoosh |
| `spotlight` | `dur` 3, `title` | Sadece arka plan kararır, kişi aydınlık kalır; isterse üstte büyük başlık. | boom |
| `orbit` | `dur` 3, `items` ["Monti"], `turns` 0.35 | Kafanın üstünde sarı halka, etiketler döner; arka yarısı saçın arkasından geçer. | whoosh |

`spotlight` ve `orbit` her karede kişiyi arka plandan ayırır (Mac'te Apple Vision, Windows'ta MediaPipe), bu yüzden birkaç saniye sürer. Pencere, başladığı
kesim parçasının sonunda kırpılır: efekti bir kesimin üstüne yayma.

## Kapanış

`outro` verilirse `save_at` anında göğüs hizasında bir kaydet düğmesi belirir, dokunulmuş gibi basılıp sarıya dolar.
Konuşma bitince görüntü siyaha kararır; `hold` saniye boyunca beyaz hapta `text` belirir, altında sarı bir ok aşağıyı,
Reels/Shorts'ta profil resminin olduğu sol altı gösterir.
