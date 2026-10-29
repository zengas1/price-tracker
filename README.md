# Fiyat / Stok Takip Botu

Beğendiğin ürünleri periyodik kontrol edip fiyat düşünce veya stok gelince Telegram'dan bildirim gönderen basit bir script.

## 1. Kurulum

```bash
cd price-tracker
pip install -r requirements.txt
```

## 2. Telegram bot oluştur (5 dakika)

1. Telegram'da **@BotFather**'ı aç, `/newbot` yaz, adını belirle. Sana bir **bot token** verecek (örn. `123456:ABC-def...`).
2. Yeni botunla bir sohbet başlat, herhangi bir mesaj gönder (örn. "merhaba").
3. Tarayıcıda şu adrese git (TOKEN yerine kendi token'ını yaz):
   `https://api.telegram.org/botTOKEN/getUpdates`
4. Dönen JSON içinde `"chat":{"id": ...}` kısmındaki sayı senin **chat_id**'n.
5. `config.json` içindeki `bot_token` ve `chat_id` alanlarını doldur.

## 3. Takip edeceğin ürünü ekle

**En kolay yol: bota linki at.** Botunla Telegram sohbetinde bir ürün linki paylaşırsan (en fazla 2 dakika içinde) otomatik olarak `config.json`'a eklenir ve "✅ eklendi" diye onay gelir. Zaten takipteki bir link tekrar atılırsa uyarı gelir.

İstersen `config.json`'daki `products` listesine elle de ekleyebilirsin:

```json
{
  "name": "Ürün adı",
  "url": "https://...",
  "price_selector": null,
  "stock_selector": null
}
```

Script önce sayfadaki **schema.org JSON-LD** verisinden (çoğu e-ticaret sitesi, Trendyol dahil, SEO için fiyat/stok bilgisini bu şekilde gömer) isim/fiyat/stok durumunu otomatik okumayı dener — çoğu ürün için `price_selector`/`stock_selector` alanlarını boş (`null`) bırakman yeterli.

**Eğer bir site JSON-LD kullanmıyorsa** (script konsola "price_selector eşleşmedi" yazarsa), CSS selector ile manuel belirtebilirsin:
1. Ürün sayfasını Chrome'da aç.
2. Fiyatın üzerine sağ tık → **İncele** (Inspect).
3. Açılan panelde fiyatı saran HTML elementinin `class` adını gör (örn. `<span class="product-price">129,90 TL</span>` ise selector `.product-price`).
4. Bunu `price_selector` alanına yaz. Aynı mantıkla stok bilgisi için `stock_selector` da eklenebilir.

## 4. Çalıştır

```bash
python tracker.py
```

İlk çalıştırmada sadece mevcut fiyatı kaydeder (karşılaştıracak eski veri yok). İkinci çalıştırmada fiyat düşmüşse Telegram'a bildirim gelir.

## 5. Otomatik/periyodik çalıştırma

İki ayrı görev kuruldu, çünkü ikisinin ihtiyacı farklı:

- **PriceTrackerLinkListener** — her **2 dakikada** bir `check_links.py`'yi çalıştırır, sadece Telegram'a yeni link atılmış mı diye bakar (hafif işlem, sık çalışabilir). Çıktı: `link_listener.log`.
- **PriceTrackerBot** — her **30 dakikada** bir `tracker.py`'yi çalıştırır, tüm ürünlerin fiyat/stok durumunu kontrol eder (sayfa indirmek daha ağır, o yüzden seyrek). Çıktı: `tracker.log`.

Faydalı komutlar (PowerShell — `<GOREV_ADI>` yerine yukarıdaki iki isimden birini yaz):

```powershell
# Görevi hemen manuel tetikle
Start-ScheduledTask -TaskName "<GOREV_ADI>"

# Son çalıştırma zamanı ve sonucunu gör (0 = başarılı)
Get-ScheduledTaskInfo -TaskName "<GOREV_ADI>"

# Görevi geçici olarak durdur
Disable-ScheduledTask -TaskName "<GOREV_ADI>"

# Tekrar etkinleştir
Enable-ScheduledTask -TaskName "<GOREV_ADI>"

# Tamamen sil
Unregister-ScheduledTask -TaskName "<GOREV_ADI>" -Confirm:$false
```

## Neden bulutta değil de yerelde çalışıyor?

Bunu GitHub Actions'a (ücretsiz bulut) taşımayı denedik, ancak Trendyol GitHub'ın sunucu IP'lerini `blocked malicious bot` diyerek 403 ile reddediyor (Cloudflare bot koruması). Bu, sadece Trendyol'a özgü değil — çoğu büyük e-ticaret sitesi datacenter IP'lerini bu şekilde engeller. Kendi ev bağlantından gelen istekler bot olarak işaretlenmediği için yerelde sorunsuz çalışıyor. `.github/workflows/` altındaki dosyalar referans olarak duruyor (bot koruması olmayan bir site için elle tetiklenebilir) ama otomatik zamanlanmış çalışmıyorlar.

## Notlar

- Bazı siteler (özellikle JavaScript ile içerik yükleyenler) düz `requests` ile fiyatı göstermeyebilir. Böyle bir durumda karşılaşırsak Playwright tabanlı bir sürüme geçebiliriz.
- Bu araç kişisel kullanım için tasarlandı. Başkalarına açık bir servise dönüştürmeden önce hedef sitelerin kullanım şartlarını kontrol et.

## Erzurum Yaşayan Sözlük

Bu depoda ayrıca QR kodla açılan, kadın ve erkek sesli bir Erzurum atasözü/deyim sözlüğü de bulunuyor: [`erzurum-sozluk/`](erzurum-sozluk/README.md).

## Faiz Getiri Hesaplama

Tutar ve gün girerek banka mevduatı ya da para piyasası fonlarında ne kadar kazanılacağını güncel oranlarla hesaplayan sayfa; oranlar her gün GitHub Actions ile güncellenir: [`faiz-hesaplama/`](faiz-hesaplama/README.md).
