"""oranlari_guncelle.py ayristiricilarinin testleri (ag erisimi gerektirmez).

    python -m unittest discover faiz-hesaplama/tools
"""

import json
import unittest
from datetime import date, timedelta

import oranlari_guncelle as og

# teklifimgelsin.com/mevduat sayfasindaki JSON-LD'nin bicimi (Ekim 2026)
MEVDUAT_HTML = """<html><head>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>
<script type="application/ld+json">""" + json.dumps({
    "@context": "https://schema.org",
    "@type": "ItemList",
    "itemListElement": [
        {"@type": "ListItem", "position": 1, "item": {
            "@type": "DepositAccount",
            "provider": {"@type": "Organization", "name": "Ziraat Dinamik"},
            "name": "Ziraat Dinamik Mevduat Faizi",
            "interestRate": {"@type": "QuantitativeValue", "minValue": 36.5, "maxValue": 44},
            "amount": {"@type": "MonetaryAmount", "currency": "TRY", "minValue": 5000, "maxValue": 19999999}}},
        {"@type": "ListItem", "position": 2, "item": {
            "@type": "DepositAccount",
            "provider": {"@type": "Organization", "name": "Örnek Bank"},
            "name": "Örnek Vadeli",
            "interestRate": 41.25}},
        {"@type": "ListItem", "position": 3, "item": {
            "@type": "DepositAccount",
            "provider": {"@type": "Organization", "name": "Ziraat Dinamik"},
            "name": "Ziraat Dinamik Mevduat Faizi",
            "interestRate": {"minValue": 1, "maxValue": 2}}},
        {"@type": "ListItem", "position": 4, "item": {
            "@type": "DepositAccount",
            "provider": {"name": "Bozuk Bank"},
            "name": "Oransiz"}},
        {"@type": "ListItem", "position": 5, "item": {
            "@type": "DepositAccount",
            "provider": {"name": "Asiri Bank"},
            "interestRate": {"minValue": 10, "maxValue": 4400}}},
    ],
}, ensure_ascii=False) + """</script>
<script type="application/ld+json">{bozuk json</script>
</head></html>"""

TCMB_HTML = """<table class="table">
<thead><tr><th>Tarih</th><th>Borç Alma</th><th>Borç Verme</th></tr></thead>
<tbody>
<tr><td>12.09.2026</td><td>-</td><td>37,00</td></tr>
<tr><td>23.10.2026</td><td>&nbsp;-</td><td><p>36,00</p></td></tr>
<tr><td>25.07.26</td><td>-</td><td>38.50</td></tr>
</tbody></table>"""


def seri(baslangic, gun_sayisi, gunluk, atla_hafta_sonu=True):
    """Her takvim gunu `gunluk` oraninda buyuyen, hafta sonu fiyat yayimlanmayan seri."""
    fiyat, sonuc = 1.0, []
    for i in range(gun_sayisi + 1):
        g = baslangic + timedelta(days=i)
        if i:
            fiyat *= 1 + gunluk
        if not (atla_hafta_sonu and g.weekday() >= 5):
            sonuc.append((g, fiyat))
    return sonuc


class Sade(unittest.TestCase):
    def test_turkce_buyuk_harf(self):
        self.assertEqual(og.sade("PARA PİYASASI"), "para piyasasi")
        self.assertEqual(og.sade("Para Piyasası Şemsiye Fonu"), "para piyasasi semsiye fonu")

    def test_ppf_mi(self):
        self.assertTrue(og.ppf_mi({"fonKodu": "PPT", "fonUnvan": "ATLAS PORTFÖY PARA PİYASASI FONU"}))
        self.assertTrue(og.ppf_mi({"fonKodu": "X", "fonUnvan": "X FONU", "fonTurAciklama": "Para Piyasası Şemsiye Fonu"}))
        self.assertFalse(og.ppf_mi({"fonKodu": "Y", "fonUnvan": "Y PORTFÖY PARA PİYASASI SERBEST (TL) FON"}))
        self.assertFalse(og.ppf_mi({"fonKodu": "Z", "fonUnvan": "Z PORTFÖY HİSSE SENEDİ FONU", "fiyat": 1.2}))


class Tcmb(unittest.TestCase):
    def test_en_yeni_satir(self):
        p = og.politika_faizi_ayikla(TCMB_HTML)
        self.assertEqual((p["oran"], p["tarih"]), (36.0, "2026-10-23"))

    def test_tablo_yoksa_hata(self):
        with self.assertRaises(ValueError):
            og.politika_faizi_ayikla("<html>bakım çalışması</html>")


class Mevduat(unittest.TestCase):
    def test_jsonld(self):
        urunler = og.mevduatlari_ayikla(MEVDUAT_HTML)
        self.assertEqual([u["banka"] for u in urunler], ["Ziraat Dinamik", "Örnek Bank"])
        z = urunler[0]
        self.assertEqual((z["oran_min"], z["oran_max"], z["tutar_min"], z["tutar_max"]),
                         (36.5, 44.0, 5000.0, 19999999.0))
        o = urunler[1]
        self.assertEqual((o["oran_min"], o["oran_max"], o["tutar_min"]), (41.25, 41.25, None))

    def test_jsonld_yok(self):
        self.assertEqual(og.mevduatlari_ayikla("<html></html>"), [])


class Getiri(unittest.TestCase):
    def test_hafta_sonu_bosluklu_seri(self):
        s = seri(date(2026, 7, 1), 120, 0.001)
        g = og.getiri(s, 30)
        self.assertGreaterEqual(g["gun"], 30)
        self.assertLessEqual(g["gun"], 33)
        self.assertAlmostEqual(g["oran"], 1.001 ** g["gun"] - 1, places=7)

    def test_fiyat_sifirlamasi_reddedilir(self):
        s = seri(date(2026, 7, 1), 60, 0.001)
        s[-5] = (s[-5][0], s[-5][1] * 0.5)
        self.assertIsNone(og.getiri(s, 30))
        self.assertIsNotNone(og.getiri(s[:-6], 30))

    def test_yetersiz_gecmis(self):
        self.assertIsNone(og.getiri(seri(date(2026, 10, 1), 20, 0.001), 30))

    def test_fiyat_serisi(self):
        satirlar = [
            {"tarih": "2026-10-28", "fonKodu": "PPT", "fiyat": 3.44797},
            {"tarih": "2026-10-27T00:00:00", "fonKodu": "PPT", "fiyat": "3.4431"},
            {"tarih": "2026-10-26", "fonKodu": "PPT", "fiyat": None},
            {"fonKodu": "PPT", "fiyat": 3.4},
        ]
        self.assertEqual(og.fiyat_serisi(satirlar),
                         [(date(2026, 10, 27), 3.4431), (date(2026, 10, 28), 3.44797)])


class Guncelle(unittest.TestCase):
    def test_hatali_bolum_eski_veriyi_korur(self):
        eski = {"mevduat": {"liste": ["eski"]},
                "durum": {"mevduat": {"son_basari": "2026-10-28T09:41+03:00", "hata": None}}}

        def bozuk(_s):
            raise RuntimeError("kaynak kapali")

        def saglam(_s):
            return {"oran": 36.0}

        bolumler = og.BOLUMLER
        og.BOLUMLER = {"mevduat": bozuk, "politika_faizi": saglam}
        try:
            basarisiz = og.guncelle(eski, ["mevduat", "politika_faizi"], None, "2026-10-29T09:41+03:00")
        finally:
            og.BOLUMLER = bolumler
        self.assertEqual(basarisiz, ["mevduat"])
        self.assertEqual(eski["mevduat"], {"liste": ["eski"]})
        self.assertEqual(eski["durum"]["mevduat"],
                         {"son_basari": "2026-10-28T09:41+03:00", "hata": "kaynak kapali"})
        self.assertEqual(eski["politika_faizi"], {"oran": 36.0})


if __name__ == "__main__":
    unittest.main()
