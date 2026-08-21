"""Basit fiyat/stok takip botu.

config.json'daki ürünleri tek tek kontrol eder, fiyat düşerse veya stok
gelirse Telegram üzerinden bildirim gönderir. Her çalıştırmada son bilinen
durumu state.json'a kaydeder, böylece bir sonraki çalıştırmada neyin
değiştiğini anlayabilir.
"""

import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from logsetup import redirect_output
from notifier import send_message

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
STATE_PATH = BASE_DIR / "state.json"

redirect_output(BASE_DIR / "tracker.log")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_telegram_config(config: dict) -> dict:
    """Telegram bilgilerini önce ortam değişkenlerinden (GitHub Actions secrets),
    yoksa config.json'daki telegram alanından okur."""
    telegram = config.get("telegram", {})
    return {
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN") or telegram.get("bot_token"),
        "chat_id": os.environ.get("TELEGRAM_CHAT_ID") or telegram.get("chat_id"),
    }


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def parse_price(text: str):
    """'1.234,56 TL' veya '1234.56' gibi metinleri float'a çevirir."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.-]", "", text).strip()
    if not cleaned:
        return None
    # Türkçe format: binlik nokta, ondalık virgül -> "1.234,56" -> "1234.56"
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_soup(url: str):
    """Sayfayı çeker ve BeautifulSoup nesnesi döner. Başarısız olursa (None, hata) döner."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        return None, str(exc)
    return BeautifulSoup(response.text, "html.parser"), None


def extract_from_jsonld(soup: BeautifulSoup):
    """Sayfadaki schema.org Product JSON-LD bloğundan isim/fiyat/stok okumaya çalışır.

    Birçok e-ticaret sitesi (Trendyol dahil) SEO için ürün bilgisini
    <script type="application/ld+json"> içine schema.org formatında gömer.
    Bu, CSS class'larına göre çok daha kararlı bir kaynaktır.
    """
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict) or item.get("@type") != "Product":
                continue
            offers = item.get("offers")
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if not isinstance(offers, dict):
                continue

            price = parse_price(str(offers.get("price", "")))
            availability = offers.get("availability", "")
            in_stock = None
            if "InStock" in availability or "LimitedAvailability" in availability:
                in_stock = True
            elif "OutOfStock" in availability:
                in_stock = False
            return item.get("name"), price, in_stock
    return None, None, None


def check_product(product: dict, state: dict, telegram: dict) -> None:
    name = product["name"]
    url = product["url"]
    price_selector = product.get("price_selector")
    stock_selector = product.get("stock_selector")

    soup, error = fetch_soup(url)
    if soup is None:
        print(f"[{name}] Sayfa alınamadı: {error}")
        return

    _, price, in_stock = extract_from_jsonld(soup)

    if price is None and price_selector:
        el = soup.select_one(price_selector)
        if el:
            price = parse_price(el.get_text())
        else:
            print(f"[{name}] price_selector eşleşmedi, siteyi/selector'ü kontrol et.")

    if in_stock is None and stock_selector:
        in_stock = soup.select_one(stock_selector) is not None

    previous = state.get(url, {})
    prev_price = previous.get("price")
    prev_in_stock = previous.get("in_stock")

    messages = []
    if price is not None and prev_price is not None and price < prev_price:
        messages.append(f"💰 {name} fiyatı düştü: {prev_price} -> {price}")
    if in_stock is True and prev_in_stock is False:
        messages.append(f"📦 {name} tekrar stokta! {url}")

    for msg in messages:
        print(msg)
        bot_token = telegram.get("bot_token")
        chat_id = telegram.get("chat_id")
        if bot_token and chat_id:
            send_message(bot_token, chat_id, msg)

    state[url] = {"name": name, "price": price, "in_stock": in_stock}
    print(f"[{name}] fiyat: {price}  stok: {in_stock}")


def main() -> None:
    config = load_config()
    state = load_state()
    telegram = get_telegram_config(config)

    for product in config.get("products", []):
        check_product(product, state, telegram)

    save_state(state)


if __name__ == "__main__":
    main()
