"""GECICI: Veri kaynaklarinin GitHub Actions'tan nasil yanit verdigini inceler."""
import json
import re
from datetime import date, timedelta

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"})


def ozet(ad, r):
    t = r.text
    title = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    print(f"== {ad}: {r.status_code} {len(t)} bayt, final={r.url}")
    print("   title:", (title.group(1).strip()[:120] if title else None))
    print("   next_data:", "__NEXT_DATA__" in t, " nuxt:", "__NUXT__" in t,
          " ld+json:", t.count("application/ld+json"), " <table:", t.lower().count("<table"),
          " %:", t.count("%"))
    for banka in ("Ziraat", "Akbank", "Enpara", "Garanti"):
        i = t.find(banka)
        if i >= 0:
            print(f"   [{banka}] ...{re.sub(r'\s+', ' ', t[max(0, i-200):i+300])}...")
            break
    apis = sorted(set(re.findall(r"https?://[a-z0-9.-]*(?:api|service|gateway)[a-z0-9.-]*\.[a-z]+[^\"' <>)]*", t)))[:25]
    print("   api-benzeri:", apis)


def dene(ad, url, **kw):
    try:
        r = s.get(url, timeout=30, **kw)
        ozet(ad, r)
        return r
    except Exception as e:
        print(f"== {ad}: HATA {e!r}")


# 1) TEFAS
try:
    r0 = s.get("https://www.tefas.gov.tr/TarihselVeriler.aspx", timeout=30)
    print("== TEFAS ana sayfa:", r0.status_code, len(r0.text), r0.text[:200].replace("\n", " "))
    for geri in range(1, 6):
        g = (date.today() - timedelta(days=geri)).strftime("%d.%m.%Y")
        r = s.post("https://www.tefas.gov.tr/api/DB/BindHistoryInfo",
                   data={"fontip": "YAT", "sfontur": "", "fonkod": "", "fongrup": "",
                         "bastarih": g, "bittarih": g, "fonturkod": "", "fonunvantip": "",
                         "kurucukod": ""},
                   headers={"X-Requested-With": "XMLHttpRequest",
                            "Origin": "https://www.tefas.gov.tr",
                            "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx",
                            "Accept": "application/json, text/javascript, */*; q=0.01"},
                   timeout=60)
        print("== TEFAS BindHistoryInfo", g, r.status_code, len(r.text), r.headers.get("content-type"))
        try:
            d = r.json()
        except Exception:
            print("   json degil:", r.text[:300].replace("\n", " "))
            continue
        rows = d.get("data") or []
        ppf = [x for x in rows if "PARA P" in (x.get("FONUNVAN") or "").upper()]
        print("   kayit:", len(rows), " ppf:", len(ppf), " anahtarlar:", list(d.keys()))
        for x in ppf[:5]:
            print("   ", json.dumps(x, ensure_ascii=False))
        if rows:
            break
    r = s.post("https://www.tefas.gov.tr/api/DB/BindComparisonFundReturns",
               data={"calismatipi": "2", "fontip": "YAT", "sfontur": "", "kurucukod": "",
                     "fongrup": "", "bastarih": "Başlangıç", "bittarih": "Bitiş",
                     "fonturkod": "", "fonunvantip": "", "strperiod": "1,1,1,1,1,1,1",
                     "islemdurum": "1"},
               headers={"X-Requested-With": "XMLHttpRequest",
                        "Origin": "https://www.tefas.gov.tr",
                        "Referer": "https://www.tefas.gov.tr/FonKarsilastirma.aspx"},
               timeout=60)
    print("== TEFAS BindComparisonFundReturns", r.status_code, len(r.text), r.text[:600].replace("\n", " "))
except Exception as e:
    print("== TEFAS HATA", repr(e))

# 2) TCMB politika faizi
dene("TCMB 1 hafta repo",
     "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/Merkez+Bankasi+Faiz+Oranlari/1+Hafta+Repo")

# 3) Banka mevduat oranlari icin aday siteler
for ad, url in [
    ("hangikredi", "https://www.hangikredi.com/yatirim-araclari/mevduat-faiz-oranlari"),
    ("hangikredi-hesap", "https://www.hangikredi.com/yatirim-araclari/mevduat-faiz-oranlari?amount=100000&maturity=32"),
    ("hesapkurdu", "https://www.hesapkurdu.com/mevduat"),
    ("enuygun", "https://www.enuygun.com/mevduat/"),
    ("teklifimgelsin", "https://www.teklifimgelsin.com/mevduat"),
    ("nakit.tr", "https://nakit.tr/hesaplama/mevduat"),
    ("hesapmatik", "https://hesapmatik.com/hesapla/mevduat-faizi-hesaplama/"),
    ("doviz", "https://www.doviz.com/mevduat-faiz-oranlari"),
    ("faizbul", "https://www.faizbul.com/mevduat-faiz-oranlari"),
    ("yatirimci.ai", "https://yatirimci.ai/fon/para-piyasasi-fonu-mu-mevduat-mi"),
]:
    dene(ad, url)
