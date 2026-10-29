# Faiz Getiri Hesaplama

Tutarı ve gün sayısını gir; paranın banka mevduatında ya da bir para piyasası fonunda o sürede ne kadar kazandıracağını gör. Oranlar her gün otomatik güncellenir.

- **Mevduat:** Bankaların güncel TL mevduat oranlarından birini seç. Bankanın sana verdiği oran farklıysa kendin de yazabilirsin.
- **Para piyasası fonu:** TEFAS'taki para piyasası fonlarından birini seç. Getiri, fonun son 7 gün, 30 gün ya da 3 aydaki fiyat artışından hesaplanır.
- **Kendi oranım:** İstediğin yıllık faizle ve stopajla hesapla.
- **Tüm seçenekler:** Girdiğin tutar ve süre için bütün bankalar ve fonlar net kazanca göre sıralanır. Bir satıra dokununca ayrıntısı açılır.

Sonuçta brüt kazanç, stopaj kesintisi, net kazanç, vade sonu toplam, günlük ve aylık ortalama kazanç ile net yıllık getiri gösterilir.

## Klasör yapısı

| Yol | Ne işe yarar |
|---|---|
| `index.html` | Hesaplama sayfası |
| `assets/hesap.js` | Hesap formülleri (arayüzden bağımsız) |
| `assets/app.js` | Sayfanın davranışı |
| `data/oranlar.json` | Oranlar: stopaj (elle), politika faizi, mevduat ve fonlar (otomatik) |
| `tools/oranlari_guncelle.py` | Oranları kaynaklardan çekip `data/oranlar.json`'a yazar |
| `tools/test_oranlari_guncelle.py` | Güncelleyicinin testleri |

## Adres

GitHub Pages bu depoda `main` dalından yayında. Birleştirmeden sonra sayfa şu adreste açılır:
`https://zengas1.github.io/price-tracker/faiz-hesaplama/`

Bilgisayarda denemek için (dosyayı çift tıklayarak açınca veri yüklenmez):

```bash
cd faiz-hesaplama && python -m http.server 8000   # sonra http://localhost:8000
```

## Oranlar nasıl güncelleniyor?

**Faiz Oranlari - Guncelle** GitHub Actions iş akışı her sabah 08:41'de (Türkiye saati) `tools/oranlari_guncelle.py`'yi çalıştırır ve değişen veriyi depoya commit eder. Sayfa veriyi hem kendi kopyasından hem de deponun `main` dalından okur ve hangisi daha yeniyse onu kullanır. Böylece Pages'in yeniden derlenmesini beklemeye gerek kalmaz.

| Bölüm | Kaynak |
|---|---|
| Para piyasası fonları | [TEFAS](https://www.tefas.gov.tr). Önce fon listesi alınır, sonra her para piyasası fonunun son 6 aylık fiyatları çekilir. Nitelikli yatırımcıya özel "serbest" fonlar listeye alınmaz. |
| Banka mevduat oranları | Karşılaştırma sitelerinin sayfalarına gömdüğü schema.org `DepositAccount` verisi. Sırasıyla teklifimgelsin.com, hangikredi.com, hesapkurdu.com ve enuygunfinans.com denenir; en az 5 ürün veren ilk site kullanılır. |
| Politika faizi | TCMB'nin 1 hafta vadeli repo sayfası |
| Stopaj | Elle tutulur (aşağıya bak) |

Bir kaynak yanıt vermezse o bölümün önceki verisi korunur ve sayfada uyarı çıkar. İş akışı da kırmızı görünür. Elle çalıştırmak için Actions sekmesinde **Faiz Oranlari - Guncelle → Run workflow** ya da:

```bash
pip install requests
python faiz-hesaplama/tools/oranlari_guncelle.py               # hepsi
python faiz-hesaplama/tools/oranlari_guncelle.py --bolum fonlar
python -m unittest discover -s faiz-hesaplama/tools            # testler
```

## Hesap nasıl yapılıyor?

- **Mevduat:** `brüt faiz = tutar × yıllık oran × gün / 365`, `net = brüt − stopaj`. Süre 32 günden uzunsa varsayılan olarak para 32 günlük vadelerle yenilenir ve her vade sonunda net faiz ana paraya eklenir (bileşik). Ayarlardan tek vadeye çevrilebilir. Oranın süre boyunca değişmeyeceği varsayılır.
- **Fon:** Fonun seçilen dönemdeki fiyat artışı aynı hızla sürer kabul edilir: `brüt = tutar × ((1 + dönem getirisi)^(gün / dönem günü) − 1)`. Stopaj kazanç üzerinden kesilir. Fiyatın bir günde %2'den fazla oynadığı dönemler (fon tasfiyesi, fiyat sıfırlama gibi) hesaba katılmaz.
- **Banka oranı aralığı:** Siteler oranı çoğu zaman "%36,5–%44" gibi bir aralık olarak verir. Varsayılan olarak en yüksek oran kullanılır. Bu oran genelde kampanyaya, yeni müşteriye ya da belli bir tutara bağlıdır; ayarlardan en düşük orana geçilebilir. Ürünün tutar aralığı dışında kalan girişlerde o ürün sıralamaya alınmaz.

## Stopaj oranları (elle güncellenir)

`data/oranlar.json` içindeki `stopaj` bölümünü güncelleyici değiştirmez. Şu an gerçek kişiler için geçerli oranlar:

| | Oran |
|---|---|
| TL mevduat, 6 aya kadar vade | %17,5 |
| TL mevduat, 1 yıla kadar vade | %15 |
| TL mevduat, 1 yıldan uzun vade | %10 |
| Para piyasası fonu | %17,5 |

Mevduat oranları 20.06.2026 tarihli Resmi Gazete'deki 11444 sayılı Cumhurbaşkanı Kararı ile **31.12.2026'ya kadar** uzatıldı. Bu tarih geçince sayfa uyarı gösterir. Yeni karar çıkınca `stopaj` bölümündeki oranları ve `gecerlilik` tarihini güncelle. Kullanıcı kendi stopaj oranlarını sayfadaki **Hesap ayarları** bölümünden de girebilir.

## Sınırlar

- Sonuçlar tahmindir, yatırım tavsiyesi değildir. Bankalar oranı tutara, vadeye ve müşteriye göre değiştirir; kesin oranı bankadan öğrenmek gerekir.
- Fon tahmini geçmiş getiriye dayanır. Politika faizi düştükçe fon getirileri de düşer.
- TEFAS ve karşılaştırma siteleri resmî bir API sunmuyor; sayfa ya da servis yapıları değişirse güncelleyicinin ilgili bölümünün uyarlanması gerekir. İş akışının kırmızıya dönmesi bunun işaretidir.
