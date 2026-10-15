"""Sözlük maddelerinin kadın ve erkek seslerini edge-tts ile MP3 olarak üretir.

Var olan dosyaların üzerine yazmaz: gerçek bir Erzurumlunun kaydını
ses/NN-kadin.mp3 veya ses/NN-erkek.mp3 adıyla koyarsan o korunur.

Kullanım:
    pip install edge-tts
    python erzurum-sozluk/tools/ses_uret.py             # eksik sesleri üret
    python erzurum-sozluk/tools/ses_uret.py --force     # hepsini yeniden üret
    python erzurum-sozluk/tools/ses_uret.py --only 07   # tek madde
    python erzurum-sozluk/tools/ses_uret.py --dry-run   # sadece listele
"""
import argparse
import asyncio
import json
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
HIZ = "-10%"  # yaşlıca, ağır bir anlatım için biraz yavaş


async def uret(metin, ses, hedef):
    import edge_tts

    await edge_tts.Communicate(metin, ses, rate=HIZ).save(str(hedef))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="var olan dosyaları da yeniden üret")
    parser.add_argument("--only", help="yalnızca bu id'li maddeyi üret (ör. 07)")
    parser.add_argument("--dry-run", action="store_true", help="üretmeden ne yapılacağını yaz")
    args = parser.parse_args()

    veri = json.loads((KOK / "data" / "sozluk.json").read_text(encoding="utf-8"))
    ses_dizini = KOK / "ses"
    ses_dizini.mkdir(exist_ok=True)

    uretilen = atlanan = 0
    for madde in veri["maddeler"]:
        if args.only and madde["id"] != args.only:
            continue
        for cinsiyet in ("kadin", "erkek"):
            hedef = ses_dizini / f"{madde['id']}-{cinsiyet}.mp3"
            if hedef.exists() and not args.force:
                atlanan += 1
                continue
            print(f"{hedef.name}  <- {veri['sesler'][cinsiyet]}")
            if not args.dry_run:
                await uret(madde[f"metin_{cinsiyet}"], veri["sesler"][cinsiyet], hedef)
            uretilen += 1

    eylem = "üretilecek" if args.dry_run else "üretildi"
    print(f"{uretilen} dosya {eylem}, {atlanan} var olan dosya atlandı.")


if __name__ == "__main__":
    asyncio.run(main())
