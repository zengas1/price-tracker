# Erzurum Yaşayan Sözlük

Erzurum yöresinden 30 atasözü ve deyimden oluşan, QR kodla açılan sesli bir sözlük. Her maddenin kendi sayfası var: QR okutulunca telefonda o söz açılır; Erzurum şivesiyle bir **kadın** ve bir **erkek** sesi sözü söyler ve anlamını anlatır. Sayfada ayrıca standart Türkçe karşılığı, anlamı ve örnek bir kullanım bulunur.

## Klasör yapısı

| Yol | Ne işe yarar |
|---|---|
| `data/sozluk.json` | 30 madde: şiveli söz, standart karşılık, anlam, örnek, kadın ve erkek okuma metni |
| `index.html` | Tüm sözlerin listesi, arama ve atasözü/deyim süzgeci |
| `madde.html?id=NN` | QR'ın açtığı madde sayfası (kadın/erkek ses oynatıcısı) |
| `kitapcik.html` | Yazdırılabilir A4 QR kartları (sergi, pano, kitapçık için) |
| `ses/NN-kadin.mp3`, `ses/NN-erkek.mp3` | Ses dosyaları |
| `qr/NN.svg`, `qr/sozluk.svg` | Her maddenin ve ana sayfanın QR kodu |
| `tools/ses_uret.py` | Sesleri edge-tts ile üretir |
| `tools/qr_uret.py` | QR kodlarını üretir |

## Yayına alma (GitHub Pages, ücretsiz)

1. GitHub'da depo → **Settings → Pages** → *Source: Deploy from a branch*.
2. Dal olarak bu dalı (ya da birleştirdikten sonra `main`) ve `/ (root)` klasörünü seç.
3. Birkaç dakika sonra sözlük şu adreste açılır:
   `https://zengas1.github.io/price-tracker/erzurum-sozluk/`

QR kodları bu adrese göre üretildi. Ücretsiz planda Pages için deponun **herkese açık** olması gerekir. Başka bir adres kullanacaksan QR'ları yeniden üret:

```bash
pip install qrcode
python erzurum-sozluk/tools/qr_uret.py --base-url https://yeni-adres/erzurum-sozluk/
```

Bilgisayarda denemek için (dosyayı çift tıklayarak açınca veri yüklenmez):

```bash
cd erzurum-sozluk && python -m http.server 8000   # sonra http://localhost:8000
```

## Sesler nasıl üretiliyor?

`data/` ya da `tools/` klasöründe bir değişiklik push edilince **Erzurum Sozluk - Ses ve QR** GitHub Actions iş akışı çalışır, eksik sesleri üretip depoya ekler:

- Kadın sesi: `tr-TR-EmelNeural`
- Erkek sesi: `tr-TR-AhmetNeural`

Okuma metinleri Erzurum ağzının imlasıyla yazıldı (*ğış, ğapı, çoh, yoh, gadanı alım, hele bah dadaş…*), böylece yapay ses de sözleri yöre söyleyişine yakın okur. Yine de yapay ses gerçek bir Erzurumlunun ağzını, ezgisini tam veremez; bu sesler **geçici** olarak düşünülmeli.

Elle üretmek için: `pip install edge-tts && python erzurum-sozluk/tools/ses_uret.py`

## Gerçek Erzurumlu sesleriyle değiştirme (önerilir)

Sözlüğü gerçekten "yaşayan" yapan, yöreden insanların kendi sesidir.

1. Yöreden bir kadın ve bir erkek konuşmacı bul (tercihen yaşlıca, şivesi oturmuş kişiler; köy odası, kahve, mahalle derneği, halk eğitim merkezi iyi başlangıç noktalarıdır).
2. Her maddenin `metin_kadin` / `metin_erkek` alanını rehber olarak ver, ama **ezberden değil kendi ağızlarıyla** anlatmalarını iste; kendi örneklerini, kendi hikâyelerini eklemeleri daha da değerlidir.
3. Telefonla, sessiz ve halısı/perdesi olan bir odada, ağızdan 20–30 cm uzaktan kaydet. Her madde ayrı dosya olsun.
4. Dosyaları MP3'e çevirip `ses/07-kadin.mp3`, `ses/07-erkek.mp3` gibi aynı adlarla `ses/` klasörüne koy ve push et.

Üretim betiği var olan dosyaların üzerine yazmadığı için gerçek kayıtlar korunur. Konuşmacılardan kayıtların yayımlanması için yazılı izin almayı unutma; istersen sayfaya adlarını da ekleyebiliriz.

## İçeriği doğrulama

Liste, Erzurum'da yaygın söylenen atasözü ve deyimlerden derlendi; bazıları Türkiye geneline de yayılmış sözlerin Erzurum ağzıyla söylenişidir. `dogrulandi` alanı her maddede `false` olarak duruyor: yayından önce bir Erzurumlu ya da halk bilimci (ör. Atatürk Üniversitesi Türk Halk Bilimi bölümü) şiveli yazımları ve açıklamaları gözden geçirmeli, kontrol edilen maddelerde bu alan `true` yapılmalı. Madde eklemek/değiştirmek için `data/sozluk.json` dosyasını düzenlemek yeterli; site ve QR'lar ona göre güncellenir.
