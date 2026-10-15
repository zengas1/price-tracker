"""Her sözlük maddesi için madde sayfasına giden bir QR kodu (SVG) üretir.

Kullanım:
    python erzurum-sozluk/tools/qr_uret.py
    python erzurum-sozluk/tools/qr_uret.py --base-url https://kendi-alan-adin.com/sozluk/
"""
import argparse
import json
from pathlib import Path

import qrcode
import qrcode.image.svg

KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_URL = "https://zengas1.github.io/price-tracker/erzurum-sozluk/"


def qr_kaydet(url, hedef):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
        image_factory=qrcode.image.svg.SvgPathFillImage,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image().save(hedef)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=VARSAYILAN_URL)
    args = parser.parse_args()
    base = args.base_url.rstrip("/") + "/"

    veri = json.loads((KOK / "data" / "sozluk.json").read_text(encoding="utf-8"))
    qr_dizini = KOK / "qr"
    qr_dizini.mkdir(exist_ok=True)

    qr_kaydet(base, qr_dizini / "sozluk.svg")
    for madde in veri["maddeler"]:
        qr_kaydet(f"{base}madde.html?id={madde['id']}", qr_dizini / f"{madde['id']}.svg")
    print(f"{len(veri['maddeler'])} madde + ana sayfa için QR üretildi -> {qr_dizini}")


if __name__ == "__main__":
    main()
