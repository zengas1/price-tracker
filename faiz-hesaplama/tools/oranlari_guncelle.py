"""Faiz hesaplama sayfasinin verisini (data/oranlar.json) gunceller.

Uc bolum ayri ayri cekilir:
  - politika_faizi: TCMB 1 hafta vadeli repo (politika) faizi
  - mevduat: bankalarin TL mevduat oranlari (karsilastirma sitelerinin
    sayfalarina gomdugu schema.org DepositAccount JSON-LD verisi)
  - fonlar: TEFAS'taki para piyasasi fonlarinin fiyat gecmisinden 7/30/91
    gunluk getirileri

Bir bolum cekilemezse o bolumun onceki verisi korunur, hata `durum` alanina
yazilir. `stopaj` bolumu elle tutulur, betik ona dokunmaz.

Kullanim:
    python faiz-hesaplama/tools/oranlari_guncelle.py
    python faiz-hesaplama/tools/oranlari_guncelle.py --bolum fonlar
"""

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

VERI = Path(__file__).resolve().parent.parent / "data" / "oranlar.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
TR_SAAT = timezone(timedelta(hours=3))

TCMB_URL = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/"
            "Para+Politikasi/Merkez+Bankasi+Faiz+Oranlari/1+Hafta+Repo")

# Sirayla denenir; en az MIN_URUN gecerli urun veren ilk kaynak kullanilir.
MEVDUAT_KAYNAKLARI = [
    ("teklifimgelsin.com", "https://teklifimgelsin.com/mevduat"),
    ("hangikredi.com", "https://www.hangikredi.com/yatirim-araclari/mevduat-faiz-oranlari"),
    ("hesapkurdu.com", "https://www.hesapkurdu.com/mevduat"),
    ("enuygunfinans.com", "https://www.enuygunfinans.com/mevduat/"),
]
MIN_URUN = 5

# TEFAS 2026'da eski /api/DB/Bind* servislerini kapatti; yenileri JSON alip
# `resultList` donduruyor. Fiyat servisi fon basina calisir ve `periyod` ay
# cinsinden yalnizca 1, 3, 6, 12, 36, 60 degerlerini kabul eder.
TEFAS = "https://www.tefas.gov.tr"
TEFAS_LISTE = "/api/funds/fonGetiriBazliBilgiGetir"
TEFAS_FIYAT = "/api/funds/fonFiyatBilgiGetir"
PENCERELER = (7, 30, 91)       # getiri hesaplanan donemler (gun)
GUNLUK_SICRAMA = 0.02          # PPF fiyati bir islem gununde bundan fazla oynarsa veri bozuk sayilir
BEKLEME = 1.0                  # TEFAS istekleri arasi saniye


def oturum():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5"})
    return s


def sade(metin):
    """Turkce buyuk/kucuk harf ve aksan farklarini yok sayarak karsilastirma icin."""
    metin = metin.replace("İ", "i").replace("I", "ı").lower()
    return metin.translate(str.maketrans("ıiğüşöç", "iigusoc"))


def sayi(metin):
    """'36,00' / '36.00' / '%36' -> 36.0; sayi yoksa None."""
    m = re.search(r"\d+(?:[.,]\d+)?", metin or "")
    return float(m.group(0).replace(",", ".")) if m else None


# ---------------------------------------------------------------- TCMB

def politika_faizi_ayikla(html):
    """TCMB 1 hafta repo sayfasindaki tablodan en guncel tarihli orani dondurur."""
    en_yeni = None
    for satir in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        hucreler = [re.sub(r"<[^>]+>|&nbsp;", " ", h).strip()
                    for h in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", satir, re.S | re.I)]
        if not hucreler:
            continue
        m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})", hucreler[0])
        if not m:
            continue
        oranlar = [sayi(h) for h in hucreler[1:] if sayi(h) is not None]
        if not oranlar:
            continue
        yil = int(m.group(3))
        tarih = date(yil + 2000 if yil < 100 else yil, int(m.group(2)), int(m.group(1)))
        if en_yeni is None or tarih > en_yeni[0]:
            en_yeni = (tarih, oranlar[-1])
    if en_yeni is None or not 0 < en_yeni[1] < 100:
        raise ValueError("TCMB tablosunda tarihli bir faiz satiri bulunamadi")
    return {"oran": en_yeni[1], "tarih": en_yeni[0].isoformat(), "kaynak": "TCMB", "url": TCMB_URL}


def politika_faizi(s):
    r = s.get(TCMB_URL, timeout=30)
    r.raise_for_status()
    return politika_faizi_ayikla(r.text)


# ---------------------------------------------------------------- Mevduat

def jsonld_bloklari(html):
    for blok in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
                           html, re.S | re.I):
        try:
            yield json.loads(blok)
        except json.JSONDecodeError:
            continue


def _gez(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _gez(v)
    elif isinstance(o, list):
        for v in o:
            yield from _gez(v)


def _sayiya(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return sayi(v) if isinstance(v, str) else None


def _aralik(deger):
    """schema.org QuantitativeValue / MonetaryAmount ya da duz sayi -> (min, max)."""
    if isinstance(deger, dict):
        tek = deger.get("value")
        en_az, en_cok = _sayiya(deger.get("minValue", tek)), _sayiya(deger.get("maxValue", tek))
    else:
        en_az = en_cok = _sayiya(deger)
    return (en_az if en_az is not None else en_cok), (en_cok if en_cok is not None else en_az)


def mevduatlari_ayikla(html):
    """Sayfadaki JSON-LD'den DepositAccount urunlerini cikarir."""
    urunler, gorulen = [], set()
    for blok in jsonld_bloklari(html):
        for o in _gez(blok):
            tur = o.get("@type")
            turler = tur if isinstance(tur, list) else [tur]
            if "DepositAccount" not in turler or "interestRate" not in o:
                continue
            saglayici = o.get("provider") or o.get("brand") or {}
            banka = (saglayici.get("name") if isinstance(saglayici, dict) else str(saglayici)) or ""
            urun = o.get("name") or ""
            oran_min, oran_max = _aralik(o.get("interestRate"))
            tutar_min, tutar_max = _aralik(o.get("amount"))
            if not banka.strip() or oran_max is None or not 0 <= oran_min <= oran_max \
                    or not 0 < oran_max < 100:
                continue
            anahtar = (sade(banka), sade(urun))
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            urunler.append({
                "banka": banka.strip(),
                "urun": urun.strip(),
                "oran_min": oran_min,
                "oran_max": oran_max,
                "tutar_min": tutar_min,
                "tutar_max": tutar_max,
            })
    urunler.sort(key=lambda u: -u["oran_max"])
    return urunler


def mevduat(s):
    hatalar = []
    for ad, url in MEVDUAT_KAYNAKLARI:
        try:
            r = s.get(url, timeout=30)
            r.raise_for_status()
            urunler = mevduatlari_ayikla(r.text)
        except Exception as e:  # bir kaynak cokerse siradakine gec
            hatalar.append(f"{ad}: {e}")
            continue
        if len(urunler) >= MIN_URUN:
            return {"tarih": date.today().isoformat(), "kaynak": ad, "url": url, "liste": urunler}
        hatalar.append(f"{ad}: yalnizca {len(urunler)} urun bulundu")
    raise RuntimeError("; ".join(hatalar))


# ---------------------------------------------------------------- TEFAS

def tefas_post(s, yol, govde, deneme=4):
    for i in range(deneme):
        try:
            r = s.post(TEFAS + yol, json=govde, timeout=40, headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Origin": TEFAS,
                "Referer": TEFAS + "/",
            })
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json().get("resultList") or []
        except (requests.RequestException, ValueError):
            if i == deneme - 1:
                raise
            time.sleep(10 * (i + 1))


def ppf_mi(satir):
    """Para piyasasi fonu mu? Nitelikli yatirimciya ozel serbest fonlar haric."""
    metin = sade(" ".join(str(v) for v in satir.values() if isinstance(v, str)))
    return "para piyasasi" in metin and "serbest" not in metin


def tefas_fon_listesi(s):
    satirlar = tefas_post(s, TEFAS_LISTE, {
        "dil": "TR", "fonTipi": "YAT", "kurucuKodu": None, "sfonTurKod": None,
        "fonTurAciklama": None, "islem": 1, "fonTurKod": None, "fonGrubu": None,
        "donemGetiri1a": "1", "donemGetiri3a": "1", "donemGetiri6a": "1",
        "donemGetiri1y": "1", "donemGetiriyb": "1", "donemGetiri3y": "1",
        "donemGetiri5y": "1", "basTarih": None, "bitTarih": None,
        "calismaTipi": 2, "getiriOrani": "1",
    })
    if not satirlar:
        raise RuntimeError("TEFAS fon listesi bos dondu")
    fonlar = {}
    for satir in satirlar:
        kod = satir.get("fonKodu")
        if kod and ppf_mi(satir):
            fonlar[kod] = satir.get("fonUnvan") or satir.get("fonAdi") or kod
    if not fonlar:
        raise RuntimeError("TEFAS listesinde para piyasasi fonu bulunamadi; alanlar: "
                           + ", ".join(sorted(satirlar[0].keys())))
    return fonlar


def fiyat_serisi(satirlar):
    """TEFAS fiyat satirlari -> tarihe gore sirali [(date, fiyat)]."""
    seri = {}
    for x in satirlar:
        try:
            g = date.fromisoformat(str(x["tarih"])[:10])
            f = float(x["fiyat"])
        except (KeyError, TypeError, ValueError):
            continue
        if f > 0:
            seri[g] = f
    return sorted(seri.items())


def getiri(seri, pencere):
    """Son fiyat ile `pencere` gun (ya da daha once) onceki fiyat arasindaki getiri.

    Aradaki herhangi bir gunde fiyat GUNLUK_SICRAMA'dan fazla oynadiysa (fon
    tasfiyesi, fiyat sifirlama vb.) None doner.
    """
    if len(seri) < 2:
        return None
    son_tarih, son_fiyat = seri[-1]
    hedef = son_tarih - timedelta(days=pencere)
    onceki = [i for i, (g, _) in enumerate(seri) if g <= hedef]
    if not onceki:
        return None
    bas = onceki[-1]
    if (son_tarih - seri[bas][0]).days > pencere + 7:  # arada uzun veri boslugu
        return None
    for (g0, f0), (g1, f1) in zip(seri[bas:], seri[bas + 1:]):
        if abs(f1 / f0 - 1) > GUNLUK_SICRAMA * max(1, (g1 - g0).days / 3):
            return None
    gun = (son_tarih - seri[bas][0]).days
    return {"oran": round(son_fiyat / seri[bas][1] - 1, 8), "gun": gun}


def fonlar(s):
    liste, hatalar = [], []
    for kod, ad in sorted(tefas_fon_listesi(s).items()):
        time.sleep(BEKLEME)
        try:
            seri = fiyat_serisi(tefas_post(s, TEFAS_FIYAT, {"fonKodu": kod, "dil": "TR", "periyod": 6}))
        except Exception as e:
            hatalar.append(f"{kod}: {e}")
            continue
        getiriler = {str(p): g for p in PENCERELER if (g := getiri(seri, p))}
        if not getiriler:
            continue
        liste.append({"kod": kod, "ad": ad, "fiyat": seri[-1][1],
                      "fiyat_tarihi": seri[-1][0].isoformat(), "getiri": getiriler})
    if not liste:
        raise RuntimeError("hicbir fonun fiyat gecmisi alinamadi; " + "; ".join(hatalar[:5]))
    # Fiyati uzun suredir guncellenmeyen (islem gormeyen, tasfiye edilen) fonlari ele
    en_son = max(f["fiyat_tarihi"] for f in liste)
    sinir = (date.fromisoformat(en_son) - timedelta(days=7)).isoformat()
    liste = [f for f in liste if f["fiyat_tarihi"] >= sinir]
    sonuc = {"tarih": en_son, "kaynak": "TEFAS", "url": "https://www.tefas.gov.tr", "liste": liste}
    if hatalar:
        sonuc["eksik"] = hatalar
    return sonuc


# ---------------------------------------------------------------- Ana akis

BOLUMLER = {"politika_faizi": politika_faizi, "mevduat": mevduat, "fonlar": fonlar}


def guncelle(veri, secilen, s, simdi):
    """Secilen bolumleri yerinde gunceller; basarisiz olan bolum adlarini dondurur."""
    durum = veri.setdefault("durum", {})
    basarisiz = []
    for ad in secilen:
        try:
            veri[ad] = BOLUMLER[ad](s)
            durum[ad] = {"son_basari": simdi, "hata": None}
            print(f"[tamam] {ad}")
        except Exception as e:  # bolumun eski verisi korunur
            durum[ad] = {"son_basari": (durum.get(ad) or {}).get("son_basari"), "hata": str(e)[:500]}
            basarisiz.append(ad)
            print(f"[HATA] {ad}: {e}", file=sys.stderr)
    return basarisiz


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bolum", choices=list(BOLUMLER), action="append",
                    help="yalnizca bu bolumu guncelle (birden cok verilebilir)")
    args = ap.parse_args()

    veri = json.loads(VERI.read_text(encoding="utf-8")) if VERI.exists() else {}
    simdi = datetime.now(TR_SAAT).isoformat(timespec="minutes")
    basarisiz = guncelle(veri, args.bolum or list(BOLUMLER), oturum(), simdi)
    veri["son_kontrol"] = simdi
    VERI.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # Kaynaklardan biri bozulduysa is akisi kirmizi gorunsun (veri yine de yazilir)
    if basarisiz:
        sys.exit(1)


if __name__ == "__main__":
    main()
