"""Sadece gelen Telegram mesajlarını kontrol eder (hafif, sık çalıştırılmak için).

Fiyat kontrolü (tracker.py) ağır ve 30 dakikada bir çalışıyor. Bu script
ise yalnızca yeni link var mı diye bakar, bu yüzden çok daha sık (örn. her
1-2 dakikada bir) çalıştırılabilir ve link atınca hızlı geri dönüş sağlar.
"""

import json

from link_bot import process_incoming_links
from logsetup import redirect_output
from tracker import (
    BASE_DIR,
    CONFIG_PATH,
    extract_from_jsonld,
    fetch_soup,
    get_telegram_config,
    load_config,
    load_state,
    save_state,
)

redirect_output(BASE_DIR / "link_listener.log")


def main() -> None:
    config = load_config()
    state = load_state()
    telegram = get_telegram_config(config)

    changed = process_incoming_links(config, state, telegram, fetch_soup, extract_from_jsonld)
    if changed:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("Yeni ürün eklendi, config.json güncellendi.")

    save_state(state)


if __name__ == "__main__":
    main()
